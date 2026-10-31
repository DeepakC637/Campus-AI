from django.shortcuts import render

def landing_page(request):
    """
    Renders public landing page for PlacementHub.
    """
    return render(request, 'core/landing.html')
