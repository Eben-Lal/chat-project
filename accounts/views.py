
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from .forms import RegisterForm
from .models import User
from chat.models import Message
from django.db.models import Count, Q

def register_view(request):
    form = RegisterForm(request.POST or None)
    if form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("user_list")
    return render(request, "accounts/register.html", {"form": form})

@login_required
def user_list_view(request):
    users = User.objects.exclude(id=request.user.id)

    for user in users:
        user.unread_count = Message.objects.filter(
            sender=user,
            receiver=request.user,
            is_read=False
        ).count()

    return render(request, "accounts/user_list.html", {"users": users})