from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.db.models import Sum
from django.contrib import messages
from datetime import date
from .models import Profile,Donor,DonationHistory,Receiver, BloodRequest,BloodStock, StockTransaction, BLOOD_GROUPS,CampRegistration,DonationRequest,Camp,Notification,DonationRecord
from .forms import DonorForm,ReceiverForm, BloodRequestForm

# ============================== public and Register view =================================== 

def index(request):
    return render(request, "index.html")

def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        role = request.POST.get('role')

        # Empty validation
        if not all([username, email, password1, password2, role]):
            messages.error(request, "All fields are required!")
            return redirect("register")

        # Password match
        if password1 != password2:
            messages.error(request, "Passwords do not match")
            return redirect("register")

        # Duplicate email
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered")
            return redirect("register")

        # Duplicate username
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
            return redirect("register")

        # ❗ Prevent admin registration
        role = role.strip().upper()
        if role == "ADMIN":
            messages.error(request, "Admin registration is not allowed")
            return redirect("register")

        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password1
        )

        # Create profile safely
        Profile.objects.create(user=user, role=role)

        messages.success(request, "Registration successful. Please login.")
        return redirect("login")

    return render(request, "registration.html")

# ============================== Login /password reset /logout ==============================

def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            # profile create if missing
            profile, created = Profile.objects.get_or_create(user=user)
            if user.is_superuser and profile.role != "ADMIN":
                profile.role = "ADMIN"
                profile.save()

            # safe role check
            role = (profile.role or "").strip().upper()

            # redirect based on role
            if role == "ADMIN":
                return redirect("admin_dashboard")
            elif role == "DONOR":
                 # Check if donor exists
                if Donor.objects.filter(user=user).exists():
                    return redirect("donor_dashboard")
                else:
                    return redirect("donor_register")
            elif role == 'RECEIVER':
                # Check if receiver exists
                if Receiver.objects.filter(user=user).exists():
                    return redirect("receiver_dashboard")
                else:
                    return redirect("receiver_register")
            elif role == 'STAFF':
                return redirect('staff_dashboard')
            else:
                messages.error(request,"Role not assigned properly.Contact Admin!")
                return redirect("login")

        else:
            messages.error(request, "Invalid username or password")

    return render(request, "login.html")

def forgot_password(request):
    if request.method == 'POST':
        username = request.POST.get('username')

        if User.objects.filter(username=username).exists():
            return redirect('set_new_password', username=username)
        else:
            messages.error(request, 'Username not found')

    return render(request, 'forgot_password.html')

def set_new_password(request, username):
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        messages.error(request, 'Invalid user')
        return redirect('forgot_password')

    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if new_password != confirm_password:
            messages.error(request, 'Passwords do not match')
        elif len(new_password) < 6:
            messages.error(request, 'Password must be at least 6 characters')
        else:
            user.password = make_password(new_password)
            user.save()
            messages.success(request, 'Password updated successfully')
            return redirect('login')

    return render(request, 'set_new_password.html', {'username': username})

def logout_view(request):
    logout(request)
    messages.success(request,'You have been logged out successfully')
    return redirect('index')

# =====================================ADMIN VIEWS ==========================================

@login_required
def admin_dashboard(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if (profile.role or "").strip().upper() != 'ADMIN':
        return redirect('login')

    # Counts
    total_donors = Donor.objects.count()
    total_receivers = Receiver.objects.count()
    total_staff = Profile.objects.filter(role='STAFF').count()

    # Tables data
    donors = Donor.objects.select_related('user').all()
    receivers = Receiver.objects.select_related('user').all()
    staffs = Profile.objects.filter(role='STAFF').select_related('user')

    # Pending receiver verification
    unverified_receivers = Receiver.objects.filter(
        is_verified=False
    ).select_related('user')

    # 🚨 Emergency blood requests (pending only)
    emergency_requests = BloodRequest.objects.filter(
        emergency=True,
        status='PENDING'
    ).select_related('receiver', 'receiver__user')
    context = {
        'total_donors': total_donors,
        'total_receivers': total_receivers,
        'total_staff': total_staff,
        'donors': donors,
        'receivers': receivers,
        'staffs': staffs,
        'unverified_receivers': unverified_receivers,
        'emergency_requests': emergency_requests,
        'has_emergency': emergency_requests.exists(),
    }

    return render(request, 'admin/admin_dashboard.html', context)

@login_required
def donation_requests_admin(request):
    requests = DonationRequest.objects.filter(approved=False, rejected=False)
    return render(request, 'donations/admin_requests.html', {'requests': requests})

@login_required
def all_requests(request):
    if request.user.profile.role != "ADMIN":
        messages.error(request, "Admin access required")
        return redirect("stock_report")

    requests = BloodRequest.objects.all().order_by("-created_at")
    return render(request, "blood_requests/all_requests.html", {"requests": requests})

#admin approve/reject request
@login_required
def update_request_status(request, pk, action):
    if request.user.profile.role != "ADMIN":
        messages.error(request, "Admin access required")
        return redirect("stock_report")

    blood_request = get_object_or_404(BloodRequest, pk=pk)

    if action == "approve":
        stock = BloodStock.objects.filter(
            blood_group=blood_request.blood_group
        ).first()

        if not stock or stock.units < blood_request.units_required:
            messages.error(request, "Insufficient stock")
            return redirect("all_requests")

        stock.units -= blood_request.units_required
        stock.save()
        Notification.objects.create(
    user=blood_request.receiver.user,
    message="Your blood request has been approved."
)

        StockTransaction.objects.create(
            blood_group=blood_request.blood_group,
            change=-blood_request.units_required,
            transaction_type="ISSUE"
        )

        blood_request.status = "COMPLETED"
        messages.success(request, "Request approved and stock updated")

    elif action == "reject":
        blood_request.status = "REJECTED"
        messages.warning(request, "Request rejected")

    blood_request.admin_remark = request.POST.get("remark")
    blood_request.save()
    Notification.objects.create(
    user=blood_request.receiver.user,
    message="Your blood request has been rejected."
)

    return redirect("all_requests")

# admin approve donations
@login_required
def approve_donation(request, pk):
    donation = get_object_or_404(DonationRequest, pk=pk)
    donor = donation.donor

    # Add to stock
    stock, _ = BloodStock.objects.get_or_create(
        blood_group=donor.blood_group
    )
    stock.units += donation.units
    stock.save()

    # Stock transaction
    StockTransaction.objects.create(
        blood_group=donor.blood_group,
        change=donation.units,
        transaction_type='ADD'
    )

    # Donation record
    DonationRecord.objects.create(
        donor=donor,
        blood_group=donor.blood_group,
        units=donation.units
    )
    DonationHistory.objects.create(
        donor=donor,
        date=donation.request_date,   # ✅ THIS IS THE KEY LINE
        units=donation.units
    )
    # 🔥 THIS UPDATES LAST DONATION DATE
    donor.last_donation = donation.request_date
    update_donor_availability(donor)
    donor.save()
    donation.approved = True
    donation.save()

    # Notification
    Notification.objects.create(
        user=donor.user,
        message="Your blood donation has been approved and added to stock."
    )

    return redirect('donation_requests_admin')

# admin reject donations
@login_required
def reject_donation(request, pk):
    donation = get_object_or_404(DonationRequest, pk=pk)
    donation.rejected = True
    donation.save()

    Notification.objects.create(
        user=donation.donor.user,
        message="Your blood donation request has been rejected."
    )

    return redirect('donation_requests_admin')

@login_required
def create_camp(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    # Admin-only access
    if (profile.role or "").strip().upper() != "ADMIN":
        messages.error(request, "Admin access required")
        return redirect("login")

    if request.method == "POST":
        name = request.POST.get("name")
        date_ = request.POST.get("date")
        location = request.POST.get("location")
        description = request.POST.get("description")

        if not all([name, date_, location]):
            messages.error(request, "All required fields must be filled")
            return redirect("create_camp")
        

        # ✅ First create the Camp object
        camp = Camp.objects.create(
            name=name,
            date=date_,
            location=location,
            description=description
        )

        messages.success(request, "Blood donation camp created successfully")
        # ✅ Notify ONLY available donors
        available_donors = Donor.objects.filter(available=True)

        for donor in available_donors:
            Notification.objects.create(
                user=donor.user,
                notif_type="CAMP",   # ✅ VERY IMPORTANT
                message=(
                    f"🏕 New Blood Donation Camp\n"
                    f"Name: {camp.name}\n"
                    f"Date: {camp.date}\n"
                    f"Location: {camp.location}"
                )
            )

        return redirect("camp_list_admin")

    return render(request, "camp/create_camp.html")
# admin camp list view
@login_required
def camp_list_admin(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if (profile.role or "").strip().upper() != "ADMIN":
        messages.error(request, "Admin access required")
        return redirect("login")

    camps = Camp.objects.all().order_by("-date")

    # Admin doesn’t need registrations, so just pass empty list
    registered_camps = []

    return render(request, "camp/camp_list.html", {
        "camps": camps,
        "registered_camps": registered_camps,
        "role": "ADMIN",
    })

# admin report view
@login_required
def reports(request):
    context = {
        "total_donors": Donor.objects.count(),
        "total_receivers": Receiver.objects.count(),
        "total_requests": BloodRequest.objects.count(),
        "stock": BloodStock.objects.all(),
        "monthly_donations": DonationHistory.objects.filter(
            date__month=date.today().month
        ).count(),
    }
    return render(request, "admin/reports.html", context)

@login_required
def admin_verify_receivers(request):
    if request.user.profile.role != "ADMIN":
        messages.error(request, "Unauthorized access")
        return redirect("index")

    unverified_receivers = (
        Receiver.objects
        .select_related("user")
        .filter(is_verified=False)
    )

    return render(
        request,
        "admin/verify_receivers.html",
        {"unverified_receivers": unverified_receivers}
    )

@login_required
def verify_receiver(request, receiver_id):
    if request.user.profile.role != "ADMIN":
        messages.error(request, "Unauthorized access")
        return redirect("index")

    receiver = get_object_or_404(Receiver, id=receiver_id)
    receiver.is_verified = True
    receiver.save()
    Notification.objects.create(
    user=receiver.user,
    message="Your receiver profile has been verified by admin."
)
    messages.success(
        request,
        f"{receiver.user.username} has been verified successfully."
    )
    return redirect("admin_verify_receivers")

@login_required
def reject_receiver(request, receiver_id):
    if request.user.profile.role != "ADMIN":
        messages.error(request, "Unauthorized access")
        return redirect("index")

    receiver = get_object_or_404(Receiver, id=receiver_id)

    # Option 1: delete receiver completely
    receiver.delete()
    Notification.objects.create(
    user=receiver.user,
    message="Your receiver profile has been rejected by admin."
)
    messages.success(
        request,
        "Receiver request has been rejected."
    )
    return redirect("admin_verify_receivers")


# ===================================== DONOR VIEWS =========================================

def update_donor_availability(donor):
    if donor.last_donation:
        days = (date.today() - donor.last_donation).days
        donor.available = days >= 90
    else:
        donor.available = True

@login_required
def donor_register(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if (profile.role or "").strip().upper() != "DONOR":
        return redirect("login")

    if Donor.objects.filter(user=request.user).exists():
        return redirect("donor_dashboard")

    if request.method == "POST":
        form = DonorForm(request.POST)
        if form.is_valid():
            donor = form.save(commit=False)
            donor.user = request.user
            update_donor_availability(donor)
            donor.save()
            messages.success(request, "Donor profile created successfully")
            return redirect("donor_dashboard")
    else:
        form = DonorForm()

    return render(request, "donor/donor_register.html", {"form": form})

@login_required
def donor_dashboard(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if (profile.role or "").strip().upper() != "DONOR":
        return redirect("login")

    try:
        donor = Donor.objects.get(user=request.user)
    except Donor.DoesNotExist:
        return redirect("donor_register")

    history = DonationHistory.objects.filter(donor=donor)
    unread_notifications = Notification.objects.filter(user=request.user, is_read=False)

    unread_count=unread_notifications.count()

    return render(request, "donor/donor_dashboard.html", {
        "donor": donor,
        "history": history,
        "unread_notifications":unread_notifications,
        "unread_cout":unread_count,
    })

@login_required
def edit_donor_profile(request):
    donor = Donor.objects.get(user=request.user)

    if request.method == "POST":
        form = DonorForm(request.POST, instance=donor)
        if form.is_valid():
            donor = form.save(commit=False)
            update_donor_availability(donor)
            donor.save()
            messages.success(request, "Profile updated successfully")
            return redirect("donor_dashboard")
    else:
        form = DonorForm(instance=donor)

    return render(request, "donor/edit_donor_profile.html", {"form": form})


@login_required
def apply_donation(request):
    donor = get_object_or_404(Donor, user=request.user)

    if request.method == "POST":
        units = request.POST.get("units")
        request_date = request.POST.get("request_date")

        
        DonationRequest.objects.create(
            donor=donor,
            units=units,
            request_date=request_date
        )

        messages.success(request, "Donation request submitted successfully")
        return redirect('donation_status')

    return render(request, 'donations/apply_donation.html', {
        "today": date.today()
    })


@login_required
def donation_status(request):
    donor = get_object_or_404(Donor, user=request.user)
    requests = DonationRequest.objects.filter(donor=donor)
    return render(request, 'donations/donation_status.html', {'requests': requests})

#camp list view for donors
@login_required
def camp_list(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    allowed_roles = ["DONOR", "ADMIN"]

    if (profile.role or "").strip().upper() not in allowed_roles:
        messages.error(request, "Access denied")
        return redirect("login")

    camps = Camp.objects.all().order_by("-date")

    registered_camps = []
    if profile.role == "DONOR":
        registered_camps = CampRegistration.objects.filter(
            donor__user=request.user
        ).values_list("camp_id", flat=True)

    return render(request, "camp/camp_list.html", {
        "camps": camps,
        "registered_camps": registered_camps,
        "role": profile.role,
    })

# camp registration
@login_required
def register_camp(request, camp_id):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if profile.role != "DONOR":
        messages.error(request, "Only donors can register for camps")
        return redirect("camp_list")

    camp = get_object_or_404(Camp, id=camp_id)
    donor = get_object_or_404(Donor, user=request.user)

    if CampRegistration.objects.filter(camp=camp, donor=donor).exists():
        messages.warning(request, "Already registered for this camp")
        return redirect("camp_list")

    CampRegistration.objects.create(camp=camp, donor=donor)
    messages.success(request, "Registered for camp")
    return redirect("camp_list")


# ===================================== RECEIVER VIEWS ======================================

@login_required
def receiver_register(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if (profile.role or "").strip().upper() != "RECEIVER":
        return redirect("login")

    if Receiver.objects.filter(user=request.user).exists():
        return redirect("receiver_dashboard")

    if request.method == "POST":
        form = ReceiverForm(request.POST)
        if form.is_valid():
            receiver = form.save(commit=False)
            receiver.user = request.user
            receiver.is_verified = False
            receiver.save()
            # notify admin
            admins = User.objects.filter(profile__role="ADMIN")
            for admin in admins:
                Notification.objects.create(
        user=admin,
        message=f"New receiver '{request.user.username}' pending verification."
    )
            messages.success(request, "Receiver profile created")
            return redirect("receiver_dashboard")
    else:
        form = ReceiverForm()

    return render(request, "receiver/receiver_register.html", {"form": form})

@login_required
def receiver_dashboard(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if (profile.role or "").strip().upper() != "RECEIVER":

        return redirect("login")

    try:
        receiver = Receiver.objects.get(user=request.user)
    except Receiver.DoesNotExist:
        return redirect("receiver_register")

    requests = BloodRequest.objects.filter(receiver=receiver).order_by("-created_at")

    return render(request, "receiver/receiver_dashboard.html", {
        "receiver": receiver,
        "requests": requests
    })


@login_required
def request_blood(request):
    receiver = get_object_or_404(Receiver, user=request.user)

    if not receiver.is_verified:
        messages.error(request, "Your account is not verified yet.")
        return redirect("receiver_dashboard")

    if request.method == "POST":
        form = BloodRequestForm(request.POST)
        if form.is_valid():
            blood_request = form.save(commit=False)
            blood_request.receiver = receiver
            blood_request.status = "PENDING"
            blood_request.emergency = request.POST.get("emergency") == "on"
            blood_request.save()

            # 🔔 ADMIN POPUP
            admins = User.objects.filter(profile__role="ADMIN")
            for admin in admins:
                Notification.objects.create(
                    user=admin,
                    notif_type="EMERGENCY",
                    message=(
                        f"🚨 EMERGENCY REQUEST\n"
                        f"{blood_request.blood_group} | {blood_request.units_required} units\n"
                        f"Receiver: {receiver.user.username}"
                    )
                )

            # 🔔 DONOR POPUP (FILTERED)
            if blood_request.emergency:
                donors = Donor.objects.filter(
                    available=True,
                    blood_group=blood_request.blood_group
                )

                for donor in donors:
                    Notification.objects.create(
                        user=donor.user,
                        notif_type="EMERGENCY",
                        message=(
                            f"🚨 EMERGENCY BLOOD NEEDED!\n"
                            f"Blood Group Needed: {blood_request.blood_group}\n"
                            f"Please donate if you can."
                        )
                    )

            messages.success(request, "Emergency blood request sent successfully.")
            return redirect("receiver_dashboard")

    else:
        form = BloodRequestForm()

    return render(request, "blood_requests/request_blood.html", {"form": form})

@login_required
def my_requests(request):
    # requests = BloodRequest.objects.filter(user=request.user)
    receiver = Receiver.objects.get(user=request.user)
    requests = BloodRequest.objects.filter(receiver=receiver)
    return render(request, "blood_requests/my_requests.html", {"requests": requests})

def delete_blood_request(request, request_id):
    if request.method == 'POST':
        blood_request = get_object_or_404(BloodRequest, id=request_id)
        
        # Optional: Only allow the owner (receiver) or admin to delete
        if request.user == blood_request.receiver.user or request.user.profile.role == 'ADMIN':
            blood_request.delete()
            messages.success(request, "Blood request deleted successfully.")
        else:
            messages.error(request, "You are not allowed to delete this request.")

    return redirect('receiver_dashboard')  # or t


#===================================== NOTIFICATION VIEWS ===================================

@login_required
def notifications(request):
    notifications = Notification.objects.filter(
        user=request.user
    ).order_by("-created_at")

    unread_count = notifications.filter(is_read=False).count()

    return render(
        request,
        "notifications/notifications.html",
        {
            "notifications": notifications,
            "unread_count": unread_count
        }
    )

@login_required
def mark_notification_read(request, pk):
    if request.method != "POST":
        return redirect("notifications")

    notification = get_object_or_404(
        Notification,
        pk=pk,
        user=request.user
    )

    notification.is_read = True
    notification.save()

    return redirect("notifications")

@login_required
def mark_all_notifications_read(request):
    if request.method != "POST":
        return redirect("login")

    Notification.objects.filter(
        user=request.user,
        is_read=False
    ).update(is_read=True)

    role = (request.user.profile.role or "").strip().upper()

    if role == "ADMIN":
        return redirect("admin_dashboard")
    elif role == "DONOR":
        return redirect("donor_dashboard")
    elif role == "RECEIVER":
        return redirect("receiver_dashboard")
    elif role == "STAFF":
        return redirect("staff_dashboard")

    return redirect("login")



#================================= Staff VIEWS ==============================================


@login_required
def staff_dashboard(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if (profile.role or "").strip().upper() != 'STAFF':
        return redirect('login')

    # Total blood units
    total_units = BloodStock.objects.aggregate(total=Sum('units'))['total'] or 0

    # Blood stock levels
    blood_stocks = BloodStock.objects.all()
    stock_status = []
    for stock in blood_stocks:
        if stock.units < 5:
            status = "danger"
            tooltip = "Critical! Needs urgent replenishment."
        elif stock.units < 10:
            status = "warning"
            tooltip = "Low stock. Consider replenishing soon."
        else:
            status = "success"
            tooltip = "Sufficient stock."
        stock_status.append({
            "blood_group": stock.blood_group,
            "units": stock.units,
            "status": status,
            "tooltip": tooltip
        })

    # Pending donations
    pending_donations = DonationRequest.objects.filter(approved=False, rejected=False).select_related('donor')

    context = {
        'total_units': total_units,
        'stock_status': stock_status,
        'pending_donations': pending_donations,
    }

    return render(request, 'staff_dashboard.html', context)

# Stock Report
def stock_report(request):
    stocks = BloodStock.objects.all()
    return render(request, "inventory/stock_report.html", {"stocks": stocks})

#  Add Blood Units
def add_blood(request):
    if request.method == "POST":
        blood_group = request.POST.get("blood_group")
        units = int(request.POST.get("units"))

        stock, created = BloodStock.objects.get_or_create(
            blood_group=blood_group
        )
        stock.units += units
        stock.save()

        StockTransaction.objects.create(
            blood_group=blood_group,
            change=units,
            transaction_type="ADD"
        )

        messages.success(request, "Blood units added successfully")
        return redirect("stock_report")

    return render(request, "inventory/add_blood.html", {"blood_groups": BLOOD_GROUPS})

#  Issue Blood Units
def issue_blood(request):
    if request.method == "POST":
        blood_group = request.POST.get("blood_group")
        units = int(request.POST.get("units"))

        try:
            stock = BloodStock.objects.get(blood_group=blood_group)

            if stock.units < units:
                messages.error(request, "Not enough stock available")
                return redirect("issue_blood")

            stock.units -= units
            stock.save()

            StockTransaction.objects.create(
                blood_group=blood_group,
                change=-units,
                transaction_type="ISSUE"
            )

            messages.success(request, "Blood issued successfully")
            return redirect("stock_report")

        except BloodStock.DoesNotExist:
            messages.error(request, "Blood group not available")
            return redirect("issue_blood")

    return render(request, "inventory/issue_blood.html", {"blood_groups": BLOOD_GROUPS})

#  Transaction History
def transaction_history(request):
    transactions = StockTransaction.objects.order_by("-date")
    return render(request, "inventory/transaction_history.html", {"transactions": transactions})





