from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from accounts.models import User
from .models import Message

@login_required
def chat_room(request, user_id):
    other_user = get_object_or_404(User, id=user_id)

    messages = Message.objects.filter(
        sender__in=[request.user, other_user],
        receiver__in=[request.user, other_user]
    ).order_by("timestamp")

    # mark as read
    Message.objects.filter(
        sender=other_user,
        receiver=request.user,
        is_read=False
    ).update(is_read=True)

    room_name = f"chat_{min(request.user.id, other_user.id)}_{max(request.user.id, other_user.id)}"

    return render(request, "chat/chat.html", {
        "messages": messages,
        "other_user": other_user,
        "room_name": room_name
    })