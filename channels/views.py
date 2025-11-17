from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Channel
from .forms import ChannelForm

# Create your views here.

@login_required
def channel_list(request):
    canais = Channel.objects.filter(criado_por=request.user)
    return render(request, 'channels/channel_list.html', {'canais': canais})

@login_required
def channel_create(request):
    if request.method == 'POST':
        form = ChannelForm(request.POST)
        if form.is_valid():
            canal = form.save(commit=False)
            canal.criado_por = request.user
            canal.save()
            return redirect('channel_list')
    else:
        form = ChannelForm()
    return render(request, 'channels/channel_form.html', {'form': form})

@login_required
def channel_edit(request, pk):
    canal = get_object_or_404(Channel, pk=pk, criado_por=request.user)
    if request.method == 'POST':
        form = ChannelForm(request.POST, instance=canal)
        if form.is_valid():
            form.save()
            return redirect('channel_list')
    else:
        form = ChannelForm(instance=canal)
    return render(request, 'channels/channel_form.html', {'form': form})

@login_required
def channel_delete(request, pk):
    canal = get_object_or_404(Channel, pk=pk, criado_por=request.user)
    if request.method == 'POST':
        canal.delete()
        return redirect('channel_list')
    return render(request, 'channels/channel_confirm_delete.html', {'canal': canal})
