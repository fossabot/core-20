#  Copyright (c) 2020 Xavier Baró
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
""" Course views module """
from django.core.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.filters import SearchFilter
from rest_framework.views import Response
from rest_framework_extensions.mixins import NestedViewSetMixin

from tesla_ce.apps.api.v2.serializers import VLECourseActivityInstrumentSerializer
from tesla_ce.apps.api.v2.serializers import VLECourseActivitySerializer
from tesla_ce.models import Activity


# pylint: disable=too-many-ancestors
class VLECourseActivityViewSet(NestedViewSetMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows activity in a course to be viewed or edited.
    """
    model = Activity
    serializer_class = VLECourseActivitySerializer
    filter_backends = [SearchFilter, DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['vle_id', 'vle_activity_type', 'vle_activity_id', 'course_id', 'name']
    search_fields = ['vle_id', 'vle_activity_type', 'vle_activity_id', 'course_id', 'name']
    queryset = Activity.objects

    @action(detail=True, methods=['GET', ], url_path=r'attachment/(?P<learner_id>[\w|-]+)')
    def attachment(self, request, **kwargs):
        """
            Return the list of instruments (if any) waiting to process the attachment of the activity
        """
        activity = self.get_object()
        try:
            learner = activity.course.learners.get(learner_id=kwargs['learner_id'])
        except activity.course.learners.model.DoesNotExist:
            return Response("Learner does not exist", status=404)
        except ValidationError as verr:
            return Response(verr.__str__(), status=400)

        activity_instruments = activity.get_learner_instruments(learner)

        # Filter instruments that accept attachments
        attachment_instruments = []
        for inst in activity_instruments:
            if inst.instrument_id in [4, 5]:
                # Instruments that work with attachments (plag, fa)
                attachment_instruments.append(inst)
            elif inst.instrument_id in [1, 3]:
                # Instruments that can work with attachments (fr, vr)
                options = inst.get_options()
                if options is not None and 'offline' in options and options['offline']:
                    attachment_instruments.append(inst)
        return Response(VLECourseActivityInstrumentSerializer(instance=attachment_instruments, many=True).data)
