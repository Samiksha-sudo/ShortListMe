from django.urls import path

from app.api import auth, billing, cvs, health, jds, matches, rewrites, tailoring

urlpatterns = [
    path("health", health.health),
    path("v1/cvs", cvs.upload_cv),
    path("v1/cvs/<str:cv_id>", cvs.get_cv),
    path("v1/cvs/<str:cv_id>/export.docx", cvs.export_docx),
    path("v1/cvs/<str:cv_id>/export.pdf", cvs.export_pdf),
    path("v1/auth/signup", auth.signup),
    path("v1/auth/login", auth.login),
    path("v1/auth/refresh", auth.refresh),
    path("v1/auth/logout", auth.logout),
    path("v1/auth/forgot-password", auth.forgot_password),
    path("v1/auth/reset-password", auth.reset_password),
    path("v1/auth/account", auth.delete_account),
    path("v1/billing", billing.get_usage),
    path("v1/billing/checkout", billing.checkout),
    path("v1/billing/portal", billing.portal),
    path("v1/billing/webhook", billing.webhook),
    path("v1/jds", jds.create_jd),
    path("v1/jds/<str:jd_id>", jds.get_jd),
    path("v1/jds/<str:jd_id>/analysis", jds.analyse_jd),
    path("v1/matches", matches.create_match),
    path("v1/rewrites", rewrites.propose_rewrites),
    path("v1/tailoring", tailoring.start),
    path("v1/tailoring/<str:job_id>", tailoring.status),
]
