from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils.safestring import mark_safe
from .forms import CustomUserCreationForm
from django.contrib.auth import login
from django.shortcuts import redirect, render
from django.urls import reverse
import json


def index(request):
	return render(request, 'registration/base.html')


def base(request):
	return render(request, 'chat/index.html')


def register(request):
	if request.method == "GET":
		return render(request, "registration/register.html", {"form": CustomUserCreationForm})
	elif request.method == "POST":
		form = CustomUserCreationForm(request.POST)
		if form.is_valid():
			user = form.save()
			login(request, user)
			return redirect(reverse("chat:base"))

@login_required
def room(request, room_name): 
	return render(request, 'chat/room.html', {
		'room_name_json' : mark_safe(json.dumps(room_name)),
		'username':  mark_safe(json.dumps(request.user.username)),
	})