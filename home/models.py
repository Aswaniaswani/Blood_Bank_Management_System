from django.db import models
from django.utils.timezone import now
from django.contrib.auth.models import User

BLOOD_GROUPS = [
    ('A+', 'A+'), ('A-', 'A-'),
    ('B+', 'B+'), ('B-', 'B-'),
    ('O+', 'O+'), ('O-', 'O-'),
    ('AB+', 'AB+'), ('AB-', 'AB-'),
]

# Profile 
class Profile(models.Model):
    ROLE_CHOICES = [
        ('ADMIN', 'Admin'),
        ('DONOR', 'Donor'),
        ('RECEIVER', 'Receiver'),
        ('STAFF', 'Staff'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)

    def __str__(self):
        return self.user.username


# Donor
class Donor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    blood_group = models.CharField(max_length=3, choices=BLOOD_GROUPS)
    age = models.IntegerField(null=True, blank=True)
    weight = models.FloatField(null=True, blank=True)
    last_donation = models.DateField(null=True, blank=True)
    available = models.BooleanField(default=True)


class DonationHistory(models.Model):
    donor = models.ForeignKey(Donor, on_delete=models.CASCADE)
    date = models.DateField()
    units = models.PositiveIntegerField()


# Patient/Receiver
class Receiver(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    hospital = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    address = models.TextField()
    # emergency = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    

class BloodRequest(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('COMPLETED', 'Completed'),
    )

    receiver = models.ForeignKey(Receiver, on_delete=models.CASCADE)
    blood_group = models.CharField(max_length=3, choices=BLOOD_GROUPS)
    units_required = models.PositiveIntegerField()
    required_date = models.DateField(null=True, blank=True)
    emergency = models.BooleanField(default=False)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    admin_remark = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.receiver.user.username} - {self.blood_group} ({self.status})"
    

# Blood Stock
class BloodStock(models.Model):
    blood_group = models.CharField(max_length=3, choices=BLOOD_GROUPS, unique=True)
    units = models.PositiveIntegerField(default=0)
    def __str__(self):
        return f"{self.blood_group} - {self.units} units"

class StockTransaction(models.Model):
    TRANSACTION_TYPE = (
        ('ADD', 'Added'),
        ('ISSUE', 'Issued'),
    )
    blood_group = models.CharField(max_length=3, choices=BLOOD_GROUPS)
    change = models.IntegerField()
    transaction_type = models.CharField(max_length=5, choices=TRANSACTION_TYPE)
    date = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"{self.blood_group} ({self.transaction_type}) {self.change}"


# Donation Requests
class DonationRequest(models.Model):
    donor = models.ForeignKey(Donor, on_delete=models.CASCADE)
    units = models.PositiveIntegerField()
    request_date = models.DateField(default=now)
    approved = models.BooleanField(default=False)
    rejected = models.BooleanField(default=False)
    admin_remark = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.donor.user.username} - {self.units} units"


class DonationRecord(models.Model):
    donor = models.ForeignKey(Donor, on_delete=models.CASCADE)
    blood_group = models.CharField(max_length=3)
    units = models.PositiveIntegerField()
    donation_date = models.DateField(default=now)

    def __str__(self):
        return f"{self.donor.user.username} - {self.units} units"
    
# Notifications
class Notification(models.Model):
    NOTIF_TYPE_CHOICES = [
        ('CAMP', 'Camp'),
        ('EMERGENCY', 'Emergency'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    notif_type = models.CharField(max_length=10, choices=NOTIF_TYPE_CHOICES, default='CAMP')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    

# Camps
class Camp(models.Model):
    name = models.CharField(max_length=200)
    location = models.CharField(max_length=200)
    date = models.DateField()
    description = models.TextField(blank=True, null=True) 


class CampRegistration(models.Model):
    camp = models.ForeignKey(Camp, on_delete=models.CASCADE)
    donor = models.ForeignKey(Donor, on_delete=models.CASCADE)


