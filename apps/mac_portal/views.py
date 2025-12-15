from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import models
from django.db.models import Count, Q, F
from .models import MACPortal, MACAddress
from .serializers import MACPortalSerializer, MACAddressSerializer

class MACPortalViewSet(viewsets.ModelViewSet):
    queryset = MACPortal.objects.all()
    serializer_class = MACPortalSerializer
    
    def get_queryset(self):
        queryset = MACPortal.objects.all()
        # Fügen Sie hier Filter hinzu, falls benötigt
        return queryset

    @action(detail=False, methods=['get'])
    def stats(self, request):
        portals = self.get_queryset()
        total_portals = portals.count()
        online_portals = portals.filter(is_active=True).count()
        
        macs = MACAddress.objects.all()
        total_macs = macs.count()
        active_macs = macs.filter(status='active').count()
        
        data = {
            'total_portals': total_portals,
            'online_portals': online_portals,
            'total_macs': total_macs,
            'available_macs': macs.filter(
                status='active', 
                current_connections__lt=models.F('max_connections')
            ).count(),
            'in_use_macs': macs.filter(current_connections__gt=0).count(),
            'cooldown_macs': macs.filter(status='cooldown').count(),
            'expired_macs': macs.filter(status='expired').count(),
            'avg_health_score': 85,  # Hier können Sie die Logik für den Gesundheitswert einfügen
            'total_failovers_24h': 0,  # Hier können Sie die Failover-Statistik einfügen
            'expiring_soon': macs.filter(
                status='active',
                last_seen__isnull=False
                # Hier können Sie eine Logik für bald ablaufende MACs einfügen
            ).count(),
        }
        return Response(data)

class MACAddressViewSet(viewsets.ModelViewSet):
    queryset = MACAddress.objects.all()
    serializer_class = MACAddressSerializer
    
    def get_queryset(self):
        queryset = MACAddress.objects.all()
        portal_id = self.request.query_params.get('portal_id')
        status = self.request.query_params.get('status')
        
        if portal_id:
            queryset = queryset.filter(portal_id=portal_id)
        if status:
            queryset = queryset.filter(status=status)
            
        return queryset
    
    @action(detail=True, methods=['post'])
    def refresh(self, request, pk=None):
        mac_address = self.get_object()
        # Hier können Sie die Logik zum Aktualisieren der MAC-Adresse einfügen
        return Response({'status': 'refreshed'})

    @action(detail=False, methods=['post'])
    def bulk_refresh(self, request):
        # Hier können Sie die Logik zum Massenaktualisieren von MAC-Adressen einfügen
        return Response({'status': 'bulk refresh started'})
