from django import template

register = template.Library()


def _build_page_window(page_obj, max_visible=5):
    total_pages = page_obj.paginator.num_pages
    current_page = page_obj.number

    if total_pages <= max_visible:
        start_page = 1
        end_page = total_pages
    else:
        half_window = max_visible // 2
        start_page = max(current_page - half_window, 1)
        end_page = start_page + max_visible - 1

        if end_page > total_pages:
            end_page = total_pages
            start_page = max(end_page - max_visible + 1, 1)

    return list(range(start_page, end_page + 1))


@register.inclusion_tag("includes/compact_pagination.html")
def compact_pagination(page_obj, querystring="", page_param="page"):
    return {
        "page_obj": page_obj,
        "querystring": querystring,
        "page_param": page_param,
        "page_numbers": _build_page_window(page_obj),
    }
