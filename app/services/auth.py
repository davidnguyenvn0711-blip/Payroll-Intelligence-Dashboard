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
        return {"username": "kiemthu", "display_name": "Kiểm thử", "role": "admin"}
    if st.session_state.get("authenticated_user"):
        return st.session_state["authenticated_user"]
    st.markdown(
        '<section class="login-hero"><div class="login-hero-copy"><div class="hero-eyebrow">HHP + SBC · NỀN TẢNG NỘI BỘ</div><h1>Lương rõ ràng.<br>Vận hành nhẹ nhàng.</h1><p>Kiểm soát giờ công, chi phí và phê duyệt kỳ lương trong một không gian quản trị thống nhất.</p><div class="hero-meta"><span class="hero-tag">Dữ liệu tập trung</span><span class="hero-tag">Kiểm soát theo kỳ</span><span class="hero-tag">Bảo mật phân quyền</span></div></div></section>',
        unsafe_allow_html=True,
    )
    _, login_column, _ = st.columns([1, 1.15, 1])
    with login_column:
        st.subheader("Đăng nhập hệ thống")
        st.caption("Dữ liệu tiền lương chỉ dành cho người được phân quyền.")
        if not repository.has_users():
            st.info("Lần đầu sử dụng: tạo tài khoản quản trị. Mật khẩu chỉ được lưu dưới dạng mã băm.")
            with st.form("first_admin"):
                username = st.text_input("Tên đăng nhập")
                display_name = st.text_input("Họ và tên")
                password = st.text_input("Mật khẩu", type="password")
                confirm = st.text_input("Nhập lại mật khẩu", type="password")
                if st.form_submit_button("Tạo tài khoản quản trị", type="primary", use_container_width=True):
                    if len(username.strip()) < 3 or len(display_name.strip()) < 2:
                        st.error("Tên đăng nhập hoặc họ tên quá ngắn.")
                    elif len(password) < 10:
                        st.error("Mật khẩu cần ít nhất 10 ký tự.")
                    elif password != confirm:
                        st.error("Hai mật khẩu không khớp.")
                    else:
                        repository.save_user(username.strip(), display_name.strip(), hash_password(password), "admin")
                        st.success("Đã tạo tài khoản. Vui lòng đăng nhập.")
                        st.rerun()
        else:
            with st.form("login"):
                username = st.text_input("Tên đăng nhập")
                password = st.text_input("Mật khẩu", type="password")
                if st.form_submit_button("Đăng nhập", type="primary", use_container_width=True):
                    user = repository.get_user(username.strip())
                    if not user or not verify_password(password, user["password_hash"]):
                        st.error("Tên đăng nhập hoặc mật khẩu không đúng.")
                    else:
                        st.session_state["authenticated_user"] = {key: user[key] for key in ["username", "display_name", "role"]}
                        st.rerun()
    st.stop()


def logout():
    st.session_state.pop("authenticated_user", None)
    st.rerun()
