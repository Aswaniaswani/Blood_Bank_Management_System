from django.urls import path
from . import views

urlpatterns = [
    path('',views.index,name='index'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('set-password/<str:username>/', views.set_new_password, name='set_new_password'),

    # ================= DASHBOARDS =================
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),
    path('donor/dashboard/', views.donor_dashboard, name='donor_dashboard'),
    path('receiver/dashboard/', views.receiver_dashboard, name='receiver_dashboard'),
    path('staff/dashboard/', views.staff_dashboard, name='staff_dashboard'),

    # ================= DONOR =================
    path('donor/register/', views.donor_register, name='donor_register'),
    path('donor/edit/', views.edit_donor_profile, name='edit_donor_profile'),

    # ================= RECEIVER =================
    path('receiver/register/', views.receiver_register, name='receiver_register'),
    path('blood/request/', views.request_blood, name='request_blood'),
    path('blood/my-requests/', views.my_requests, name='my_requests'),
    path('delete_request/<int:request_id>/', views.delete_blood_request, name='delete_blood_request'),

    # ================= BLOOD REQUEST (ADMIN) =================
    path('blood/all-requests/', views.all_requests, name='all_requests'),
    path('blood/update/<int:pk>/<str:action>/', views.update_request_status, name='update_request_status'),

    # ================= DONATION MODULE =================
    # Donor
    path('donation/apply/', views.apply_donation, name='apply_donation'),
    path('donation/status/', views.donation_status, name='donation_status'),

    # Admin
    path('donation/admin/requests/', views.donation_requests_admin, name='donation_requests_admin'),
    path('donation/admin/approve/<int:pk>/', views.approve_donation, name='approve_donation'),
    path('donation/admin/reject/<int:pk>/', views.reject_donation, name='reject_donation'),

    # ================= INVENTORY =================
    path('stock/', views.stock_report, name='stock_report'),
    path('stock/add/', views.add_blood, name='add_blood'),
    path('stock/issue/', views.issue_blood, name='issue_blood'),
    path('stock/transactions/', views.transaction_history, name='transaction_history'),

    # ================= REPORTS =================
    path('reports/', views.reports, name='reports'),

    path("dashboard/admin/receivers/", views.admin_verify_receivers, name="admin_verify_receivers"),
    path("dashboard/admin/receiver/verify/<int:receiver_id>/", views.verify_receiver, name="verify_receiver"),
    path("dashboard/admin/receivers/<int:receiver_id>/reject/",views.reject_receiver,name="reject_receiver"),


    # ================= Camps ====================
    path("camps/", views.camp_list, name="camp_list"),
    path("camps/register/<int:camp_id>/", views.register_camp, name="register_camp"),

    # ================= Admin Camps =================
    path("dashboard/admin/camps/", views.camp_list_admin, name="camp_list_admin"),
    path("dashboard/admin/camps/create/", views.create_camp, name="create_camp"),

    # ================= Notifications ===============
    path("notifications/", views.notifications, name="notifications"),
    path("notifications/read/<int:pk>/", views.mark_notification_read, name="mark_notification_read"),
    path('notifications/mark_all_read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),

]


