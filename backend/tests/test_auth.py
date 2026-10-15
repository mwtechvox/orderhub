import pytest
from rest_framework.test import APIClient

from apps.companies.models import Company

pytestmark = pytest.mark.django_db


def test_unauthorized():
    assert APIClient().get("/api/companies/").status_code == 403


def test_login_csrf_and_logout(tenant):
    client = APIClient(enforce_csrf_checks=True)
    assert (
        client.post(
            "/api/auth/login/", {"username": "agent", "password": "test-password"}
        ).status_code
        == 403
    )
    csrf = client.get("/api/auth/csrf/").data["csrfToken"]
    response = client.post(
        "/api/auth/login/",
        {"username": "agent", "password": "test-password"},
        HTTP_X_CSRFTOKEN=csrf,
    )
    assert response.status_code == 200
    assert client.get("/api/auth/me/").data["username"] == "agent"
    assert (
        client.post("/api/auth/logout/", HTTP_X_CSRFTOKEN=response.data["csrfToken"]).status_code
        == 200
    )
    assert client.get("/api/auth/me/").status_code == 403


def test_company_isolation_and_creation(tenant):
    company, _, client = tenant
    other = Company.objects.create(name="Other", slug="other")
    assert client.get(f"/api/companies/{other.pk}/").status_code == 404
    assert client.post(f"/api/companies/{other.pk}/select/").status_code == 404
    assert client.get("/api/companies/").data["results"][0]["id"] == str(company.pk)
    response = client.post("/api/companies/", {"name": "New", "slug": "new"})
    assert response.status_code == 201
    assert client.post(f"/api/companies/{response.data['id']}/select/").status_code == 200
