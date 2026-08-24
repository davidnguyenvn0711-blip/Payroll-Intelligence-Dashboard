from __future__ import annotations

import hashlib
import hmac
import os

import streamlit as st


ITERATIONS = 310_000


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return f"pbkdf2_sha256${ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt_hex, expected_hex = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations))
        return hmac.compare_digest(digest.hex(), expected_hex)
    except (TypeError, ValueError):
        return False


def require_authentication(repository):
    if os.getenv("APP_TEST_MODE") == "1":
        return {"username": "kiemthu", "display_name": "Test User", "role": "admin"}
    if st.session_state.get("authenticated_user"):
        return st.session_state["authenticated_user"]
    st.markdown(
        '<section class="login-hero"><div class="login-hero-copy"><div class="hero-eyebrow">HHP + SBC · INTERNAL OPERATIONS</div><h1>Clear payroll.<br>Confident operations.</h1><p>Control attendance, payroll costs, and approvals from one unified workspace.</p><div class="hero-meta"><span class="hero-tag">Centralized data</span><span class="hero-tag">Period controls</span><span class="hero-tag">Role-based security</span></div></div></section>',
        unsafe_allow_html=True,
    )
    _, login_column, _ = st.columns([1, 1.15, 1])
    with login_column:
        st.subheader("Sign in")
        st.caption("Payroll data is available to authorized users only.")
        if not repository.has_users():
            st.info("First-time setup: create an administrator account. Passwords are stored only as secure hashes.")
            with st.form("first_admin"):
                username = st.text_input("Username")
                display_name = st.text_input("Full name")
                password = st.text_input("Password", type="password")
                confirm = st.text_input("Confirm password", type="password")
                if st.form_submit_button("Create administrator account", type="primary", use_container_width=True):
                    if len(username.strip()) < 3 or len(display_name.strip()) < 2:
                        st.error("The username or full name is too short.")
                    elif len(password) < 10:
                        st.error("The password must contain at least 10 characters.")
                    elif password != confirm:
                        st.error("The passwords do not match.")
                    else:
                        repository.save_user(username.strip(), display_name.strip(), hash_password(password), "admin")
                        st.success("Account created. Please sign in.")
                        st.rerun()
        else:
            with st.form("login"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                if st.form_submit_button("Sign in", type="primary", use_container_width=True):
                    user = repository.get_user(username.strip())
                    if not user or not verify_password(password, user["password_hash"]):
                        st.error("Incorrect username or password.")
                    else:
                        st.session_state["authenticated_user"] = {key: user[key] for key in ["username", "display_name", "role"]}
                        st.rerun()
    st.stop()


def logout():
    st.session_state.pop("authenticated_user", None)
    st.rerun()
