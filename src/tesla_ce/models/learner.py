#  Copyright (c) 2020 Roger Muñoz
#
#      This program is free software: you can redistribute it and/or modify
#      it under the terms of the GNU Affero General Public License as
#      published by the Free Software Foundation, either version 3 of the
#      License, or (at your option) any later version.
#
#      This program is distributed in the hope that it will be useful,
#      but WITHOUT ANY WARRANTY; without even the implied warranty of
#      MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#      GNU Affero General Public License for more details.
#
#      You should have received a copy of the GNU Affero General Public License
#      along with this program.  If not, see <https://www.gnu.org/licenses/>.
""" Learner model module."""
import uuid

from cache_memoize import cache_memoize
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from tesla_ce.apps.api.utils import decode_json
from .informed_consent import InformedConsent
from .user import InstitutionUser


@cache_memoize(24 * 60 * 60)
def get_learner_send(learner_id):
    """
        Compute the learner SEND properties
        :param learner_id: The database id of the learner
        :type learner_id: int
        :return: SEND information for the learner
        :rtype: dict
    """
    learner = Learner.objects.get(id=learner_id)
    send_categories = learner.sendlearner_set.filter(
        models.Q(expires_at__gte=timezone.now()) | models.Q(expires_at__isnull=True)
    ).all()
    disabled_instruments = set()
    options = set()

    if send_categories is None:
        send_categories = []

    for c in send_categories:
        data = decode_json(c.category.data)
        if 'disabled_instruments' in data:
            disabled_instruments.update(data['disabled_instruments'])
        if 'enabled_options' in data:
            options.update(data['enabled_options'])

    return {
        'is_send': len(send_categories) > 0,
        'send': {
            'enabled_options': list(options),
            'disabled_instruments': list(disabled_instruments)
        }
    }


@cache_memoize(24 * 60 * 60)
def get_learner_enrolment(learner_id):
    """
        Compute the enrolment status for a learner
        :param learner_id: The database id of the learner
        :type learner_id: int
        :return: Enrolment status for the learner
        :rtype: dict
    """
    # Get the real enrolment values for instruments and providers
    learner = Learner.objects.get(id=learner_id)
    real_enrolments = learner.enrolment_set.filter(provider__enabled=True).values(
        instrument_id=models.F("provider__instrument_id")
    ).annotate(
        models.Min("percentage"), models.Max("percentage"), models.Min("can_analyse"), models.Max("can_analyse")
    ).all()
    # Compute enrolment estimation from pending enrolment samples
    pending_contribution = learner.enrolmentsample_set.filter(
        enrolmentsamplevalidation__status=1,
        enrolmentsamplevalidation__included=False
    ).values(
        provider_id=models.F("enrolmentsamplevalidation__provider"),
        instrument_id=models.F("enrolmentsamplevalidation__provider__instrument_id"),
    ).annotate(
        pending_contribution=models.Sum("enrolmentsamplevalidation__contribution")
    )
    pending_validation = learner.enrolmentsample_set.filter(status=0, enrolmentsamplevalidation__provider__enabled=True).values(
        provider_id=models.F("enrolmentsamplevalidation__provider"),
        instrument_id=models.F("enrolmentsamplevalidation__provider__instrument_id"),
    ).annotate(
        count=models.Count("enrolmentsamplevalidation__contribution")
    )
    enrolments = list(real_enrolments)
    instruments = []
    for enrol in real_enrolments:
        instruments.append(enrol['instrument_id'])
        pending = pending_contribution.filter(instrument_id=enrol['instrument_id'])
        enrol['pending'] = list(pending.all())
        enrol['not_validated'] = list(pending_validation.all())
        enrol['pending_contributions'] = min(1.0, pending_contribution.filter(
            instrument_id=enrol['instrument_id']).aggregate(models.Avg('pending_contribution')
                                                            )['pending_contribution__avg'] or 0.0)
        enrol['not_validated_count'] = int(pending_validation.filter(
            instrument_id=enrol['instrument_id']).aggregate(models.Avg('count')
                                                            )['count__avg'] or 0)
    for missing_enrolment in pending_validation.exclude(instrument_id__in=instruments).all():
        enrolments.append({
            'instrument_id': missing_enrolment['instrument_id'],
            'percentage__min': 0.0,
            'percentage__max': 0.0,
            'can_analyse__min': False,
            'can_analyse__max': False,
            'pending': [],
            'not_validated': list(pending_validation.filter(
                instrument_id=missing_enrolment['instrument_id']).all()),
            'pending_contributions': 0.0,
            'not_validated_count': int(pending_validation.filter(
                instrument_id=missing_enrolment['instrument_id']
            ).aggregate(models.Avg('count'))['count__avg'] or 0)
        })

    return enrolments


class Learner(InstitutionUser):
    """ Learner model. """
    learner_id = models.UUIDField(null=False, unique=True, blank=False,
                                  default=uuid.uuid4,
                                  help_text=_('Learner unique ID used to anonymize identity with external providers'))

    consent = models.ForeignKey(InformedConsent, null=True,
                                on_delete=models.SET_NULL, help_text=_('Current Informed consent of the learner'))

    consent_accepted = models.DateTimeField(null=True, blank=True,
                                            help_text=_('Date of acceptance of the current Informed Consent'))
    consent_rejected = models.DateTimeField(null=True, blank=True,
                                            help_text=_('Date of rejection of the current Informed Consent'))

    joined_at = models.DateTimeField(auto_now_add=True, help_text=_('Date the learner joined for this institution'))

    def __repr__(self):
        return "<Learner(learner_id='%r', consent_id='%r')>" % (
            self.learner_id, self.consent_id)

    @property
    def send(self):
        """
            SEND information for this learner
            :return: SEND summary
            :rtype: dict
        """
        return get_learner_send(self.id)

    @property
    def ic_status(self):
        """
            Informed Consent status for this learner
            :return: Informed Consent status
            :rtype: str
        """
        if self.institution.external_ic:
            return "VALID_EXTERNAL"
        if self.consent_rejected is not None:
            return "NOT_VALID_REJECTED"
        if self.consent is None:
            return "NOT_VALID_MISSING"
        return self.consent.status

    @property
    def enrolment_status(self):
        """
            Get the enrolment status for a learner
            :return: Aggregated values per instrument
        """
        return get_learner_enrolment(self.id)
