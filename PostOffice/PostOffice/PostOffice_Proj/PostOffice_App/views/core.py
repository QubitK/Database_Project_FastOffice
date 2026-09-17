from django.shortcuts import render

def home(request):
    return render(request, "core/home.html")

def mail_list(request):
    return render(request, "mail/list.html")

def mail_detail(request, mail_id):
    return render(request, "mail/detail.html", {"mail_id": mail_id})