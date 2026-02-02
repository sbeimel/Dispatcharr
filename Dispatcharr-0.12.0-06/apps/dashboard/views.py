from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from psutil import cpu_percent, virtual_memory, net_io_counters
from apps.channels.models import Stream
from django.http import JsonResponse  # ADD THIS LINE


@login_required
def dashboard_view(request):
    # Fetch system metrics
    try:
        cpu_usage = cpu_percent(interval=1)
        ram = virtual_memory()
        ram_usage = f"{ram.used / (1024 ** 3):.1f} GB / {ram.total / (1024 ** 3):.1f} GB"
        network = net_io_counters()
        network_traffic = f"{network.bytes_sent / (1024 ** 2):.1f} MB"
    except Exception as e:
        cpu_usage = "N/A"
        ram_usage = "N/A"
        network_traffic = "N/A"
        print(f"Error fetching system metrics: {e}")

    # Fetch active streams and related channels
    active_streams = Stream.objects.filter(current_viewers__gt=0).prefetch_related('channels')
    active_streams_list = [
        f"Stream {i + 1}: {stream.url or 'Unknown'} ({stream.current_viewers} viewers)"
        for i, stream in enumerate(active_streams)
    ]

    # Pass data to the template
    context = {
        "cpu_usage": f"{cpu_usage}%",
        "ram_usage": ram_usage,
        "current_streams": active_streams.count(),
        "network_traffic": network_traffic,
        "active_streams": active_streams_list,
    }
    return render(request, "dashboard/dashboard.html", context)

@login_required
def settings_view(request):
    # Placeholder for settings functionality
    return render(request, 'settings.html')

@login_required
def live_dashboard_data(request):
    try:
        cpu_usage = cpu_percent(interval=1)
        ram = virtual_memory()
        network = net_io_counters()
        ram_usage = f"{ram.used / (1024 ** 3):.1f} GB / {ram.total / (1024 ** 3):.1f} GB"
        network_traffic = f"{network.bytes_sent / (1024 ** 2):.1f} MB"

        # Mocked example data for the charts
        cpu_data = [45, 50, 60, 55, 70, 65]
        ram_data = [6.5, 7.0, 7.5, 8.0, 8.5, 9.0]
        network_data = [120, 125, 130, 128, 126, 124]

        active_streams = Stream.objects.filter(current_viewers__gt=0)
        active_streams_list = [
            f"Stream {i + 1}: {stream.url or 'Unknown'} ({stream.current_viewers} viewers)"
            for i, stream in enumerate(active_streams)
        ]

        data = {
            "cpu_usage": f"{cpu_usage}%",
            "ram_usage": ram_usage,
            "current_streams": active_streams.count(),
            "network_traffic": network_traffic,
            "active_streams": active_streams_list,
            "cpu_data": cpu_data,
            "ram_data": ram_data,
            "network_data": network_data,
        }
    except Exception as e:
        data = {
            "error": str(e)
        }
    return JsonResponse(data)
