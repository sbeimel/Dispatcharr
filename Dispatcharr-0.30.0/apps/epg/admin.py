from django.contrib import admin
from .models import EPGSource, ProgramData

@admin.register(EPGSource)
class EPGSourceAdmin(admin.ModelAdmin):
    list_display = ['name', 'source_type', 'is_active']
    list_filter = ['source_type', 'is_active']
    search_fields = ['name']

@admin.register(ProgramData)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ['title', 'get_epg_tvg_id', 'start_time', 'end_time']
    list_filter = ['epg__tvg_id', 'tvg_id']
    search_fields = ['title', 'epg__name']

    def get_epg_tvg_id(self, obj):
        return obj.epg.tvg_id if obj.epg else ''
    get_epg_tvg_id.short_description = 'Channel TVG ID'
    get_epg_tvg_id.admin_order_field = 'epg__tvg_id'
