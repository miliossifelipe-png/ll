from django.shortcuts import render

def erro_500(request):
    return render(request, 'erro.html', status=500)

def erro_404(request, exception):
    return render(request, 'erro.html', {'mensagem': 'Página não encontrada', 'codigo': 404}, status=404) 