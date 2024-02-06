from django.shortcuts import render


def Subscribe(request):
	return render(request, 'subscribe.html', {})