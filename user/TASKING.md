# `user` App Tasking Guide

This document defines the development and testing tasks to be performed in the `user` app. Please adhere strictly to the requirements and procedures specified below.

---

## Core Requirements

-   **Use Default User Model**: Directly use Django's built-in `User` model (`django.contrib.auth.models.User`).
-   **ModelForm-Based Development**: Implement all user-related forms (e.g., sign-up, update) by inheriting from `ModelForm` or Django's built-in forms.
-   **Settings Management**: When adding new apps or packages, including the `user` app, all related settings, such as registration in `INSTALLED_APPS`, must be explicitly added to `config/settings.py`.
-   **Models and Migrations**: If new models are required for a feature, they must be defined in `models.py` and applied to the database schema using the `makemigrations` and `migrate` commands.
-   **Authentication and Data Validation**: All views must enforce proper authentication (e.g., `@login_required`), and data passed through forms must be thoroughly validated.
-   **Admin Registration**: All developed models must be registered in `admin.py` so they can be easily viewed and managed from the admin page.
-   **Exclude Image Processing**: Do not implement features for user profile images or any other image uploads and processing.

---

## Detailed Task List

It is recommended to develop each feature in the following order: **Form → View → URL → Template → Write Test Code**.

### 1. Sign Up

-   [x] **Create Form**: Implement a `SignupForm` that inherits from Django's `UserCreationForm` and meets the **[Sign Up Form Specifications]** below.
-   [x] **Create View**: Implement a class-based `SignupView` that uses the `SignupForm` to create a new user. Redirect to the login page upon successful sign-up.
-   [x] **Connect URL**: Map the `SignupView` to the `/accounts/signup/` path.
-   [x] **Create Template**: Create the `signup.html` template according to the **[Template Specifications]**.
-   **Write Pytest Code**:
    -   [x] `test_signup_success`: Test successful sign-up with valid information.
    -   [x] `test_signup_fail_duplicate_username`: Test failure when signing up with a duplicate `username`.
    -   [x] `test_signup_fail_duplicate_email`: Test failure when signing up with a duplicate `email`.
    -   [x] `test_signup_fail_password_mismatch`: Test failure when the two password fields do not match.

### 2. Login & Logout

-   [x] **Implement View/Form**: Utilize Django's built-in `AuthenticationForm`, `LoginView`, and `LogoutView`.
-   [x] **Connect URL**: Set up paths for `/accounts/login/` and `/accounts/logout/`.
-   [x] **Create Template**: Create the `login.html` template according to the **[Template Specifications]**.
-   **Write Pytest Code**:
    -   [x] `test_login_success`: Test successful login with valid credentials.
    -   [x] `test_login_fail_wrong_password`: Test login failure with an incorrect password.
    -   [x] `test_logout`: Test that logout is processed correctly.

### 3. User Update

-   [x] **Create Form**: Based on `UserChangeForm`, implement a `UserUpdateForm` that only includes fields the user can modify (e.g., name, email).
-   [x] **Create View**: Implement a `UserUpdateView` with the `@login_required` decorator, allowing only logged-in users to update their own information.
-   [x] **Connect URL**: Map the `UserUpdateView` to the `/accounts/update/` path.
-   [x] **Create Template**: Create the `update.html` template according to the **[Template Specifications]**.
-   **Write Pytest Code**:
    -   [x] `test_update_success`: Test successful information update by a logged-in user.
    -   [x] `test_update_fail_unauthenticated`: Test that an unauthenticated user attempting to access the page is redirected to the login page.

### 4. Withdrawal

-   [x] **Create View**: Implement a `UserDeleteView` that deactivates the user by setting the `is_active` field to `False`, instead of actually deleting them.
-   [x] **Connect URL**: Map the `UserDeleteView` to the `/accounts/delete/` path, ensuring it goes through a confirmation step.
-   [x] **Create Template**: Create a `delete_confirm.html` template for final withdrawal confirmation, following the **[Template Specifications]**.
-   **Write Pytest Code**:
    -   [x] `test_delete_success`: Test that a logged-in user is successfully deactivated.
    -   [x] `test_delete_and_login_fail`: Test that a deactivated account cannot log in.

---

## Specifications

### **Sign Up Form Specifications**

-   **Required Fields**: `username`, `email`, `password`, `password2`
-   **Data Validation**:
    -   `username` and `email` must be unique and cannot already exist in the database.
    -   The values of the `password` and `password2` fields must match. If they don't, a validation error must be raised.
    -   Passwords must pass Django's default password validators.

### **Template Specifications**

-   **Framework**: All templates must use **Bootstrap 5** for basic styling (using the CDN is acceptable).
-   **Structure**: Create a `base.html` template. All other templates should extend it to maintain a consistent layout (e.g., navigation bar, footer).
-   **Rendering Method**: **Do not use third-party packages** that automatically render forms, such as `django-crispy-forms`. All forms and HTML components must be written manually using pure Bootstrap 5's HTML, CSS, and JavaScript.
-   **Form Rendering**: Render Django form fields and error messages using appropriate Bootstrap 5 classes (e.g., `div`, `label`, `input`, `span.text-danger`).

---

## Test Code Writing Guidelines

-   **Write Immediately**: As soon as a feature is complete, write the corresponding test code for it.
-   **Use `conftest.py`**: Utilize fixtures defined in the project's root `conftest.py` (e.g., `client`, `test_user`) to maintain a consistent testing environment.
-   **Simple Unit Tests**: Focus on simple unit tests that verify the core logic of Views and Forms.
-   **One Test, One Function Principle**: Each test function must verify **only one scenario or piece of functionality**. (e.g., separate `test_user_can_access_update_page` and `test_guest_cannot_access_update_page`).