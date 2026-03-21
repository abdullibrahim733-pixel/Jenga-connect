from django import template

register = template.Library()


@register.filter(name="absolute_uri")
def absolute_uri(path, request):
    if not path or not request:
        return path
    try:
        return request.build_absolute_uri(path)
    except Exception:
        return path
