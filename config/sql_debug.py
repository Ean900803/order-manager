"""全域 SQL 偵錯面板。

當 settings.SQL_DEBUG 為 True 時，攔截每個 HTML 回應，
把這次請求實際送進資料庫的所有 SQL 附在頁尾（可收合）。
與 DEBUG 無關，正式環境把 SQL_DEBUG 設成 False 即可停用。
"""
from django.conf import settings
from django.core.exceptions import MiddlewareNotUsed
from django.db import connection, reset_queries
from django.utils.html import escape


class SQLDebugMiddleware:
    def __init__(self, get_response):
        if not getattr(settings, "SQL_DEBUG", False):
            raise MiddlewareNotUsed
        self.get_response = get_response

    def __call__(self, request):
        # 即使 DEBUG=False 也強制記錄查詢
        connection.force_debug_cursor = True
        reset_queries()

        response = self.get_response(request)

        content_type = response.get("Content-Type", "")
        if "text/html" not in content_type or not hasattr(response, "content"):
            return response

        queries = connection.queries
        if queries:
            rows = "".join(
                f'<div class="py-1 border-bottom border-secondary">'
                f'<span class="text-info">[{q["time"]}s]</span> {escape(q["sql"])}</div>'
                for q in queries
            )
        else:
            rows = '<div class="text-muted">（這個頁面沒有 SQL 查詢）</div>'

        panel = (
            '<div class="container-fluid my-3">'
            '<button class="btn btn-sm btn-outline-info" type="button" '
            'data-bs-toggle="collapse" data-bs-target="#__sqlpanel">'
            f'<i class="bi bi-database me-1"></i>顯示 / 隱藏 本頁 SQL（{len(queries)} 條）'
            '</button>'
            '<div class="collapse mt-2" id="__sqlpanel">'
            '<div class="card card-body bg-dark text-light small" '
            'style="font-family:monospace; white-space:pre-wrap; word-break:break-all;">'
            f'{rows}</div></div></div>'
        )

        try:
            content = response.content.decode(response.charset)
        except (UnicodeDecodeError, LookupError):
            return response

        if "</body>" in content:
            content = content.replace("</body>", panel + "</body>", 1)
            response.content = content.encode(response.charset)
            if response.has_header("Content-Length"):
                response["Content-Length"] = str(len(response.content))
        return response
