from django.views import View
from django.shortcuts import render
from django.http import JsonResponse
from rest_framework.parsers import JSONParser
from .models import EPGSource, ProgramData  # Updated: import ProgramData instead of Program
from .serializers import EPGSourceSerializer
from django.utils import timezone
from datetime import timedelta


def epg_view(request):
    """
    Renders the TV guide using programmes from the next 12 hours,
    grouped by channel (via EPGData).
    """
    now = timezone.now()
    end_time = now + timedelta(hours=12)
    print(f"[EPG VIEW] Now: {now} | End Time: {end_time}")

    # Query ProgramData within the time range
    programmes = ProgramData.objects.filter(
        start_time__gte=now,
        start_time__lte=end_time
    ).order_by('start_time')
    print(f"[EPG VIEW] Found {programmes.count()} programme(s) between now and end_time.")

    # Group programmes by channel (retrieved via the EPGData parent)
    channels = {}
    for prog in programmes:
        # Assume that the EPGData instance (prog.epg) has a link to a Channel.
        channel = prog.epg.channel if prog.epg and prog.epg.channel else None
        if not channel:
            continue
        channels.setdefault(channel, []).append(prog)

    if not channels:
        print("[EPG VIEW] No channels with programmes found.")
    else:
        for channel, progs in channels.items():
            print(f"[EPG VIEW] Channel: {channel} has {len(progs)} programme(s).")

    context = {
        'channels': channels,
        'now': now,
        'end_time': end_time,
    }
    return render(request, 'epg/tvguide.html', context)


class EPGDashboardView(View):
    def get(self, request, *args, **kwargs):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            sources = EPGSource.objects.all()
            serializer = EPGSourceSerializer(sources, many=True)
            return JsonResponse({'data': serializer.data}, safe=False)
        return render(request, 'epg/epg.html', {'epg_sources': EPGSource.objects.all()})

    def post(self, request, *args, **kwargs):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            data = JSONParser().parse(request)
            serializer = EPGSourceSerializer(data=data)
            if serializer.is_valid():
                serializer.save()
                return JsonResponse({'success': True, 'data': serializer.data}, status=201)
            return JsonResponse({'success': False, 'errors': serializer.errors}, status=400)
        return JsonResponse({'success': False, 'error': 'Invalid request.'}, status=400)
