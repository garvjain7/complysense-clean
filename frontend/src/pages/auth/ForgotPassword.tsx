// Use: Forgot Password page — always shows success state to prevent user enumeration.

import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Mail, CheckCircle, ArrowLeft, RefreshCw, AlertTriangle } from "lucide-react";
import { forgotPassword } from "../../lib/auth";

export default function ForgotPassword() {
  const navigate = useNavigate();
  const [email, setEmail]           = useState("");
  const [loading, setLoading]       = useState(false);
  const [submitted, setSubmitted]   = useState(false);
  const [mailUnavailable, setMailUnavailable] = useState(false);
  const [noticeMessage, setNoticeMessage]     = useState("");
  const [resendCooldown, setResendCooldown] = useState(0);

  // Resend countdown
  useEffect(() => {
    if (resendCooldown <= 0) return;
    const id = setInterval(() => {
      setResendCooldown((v) => (v <= 1 ? 0 : v - 1));
    }, 1000);
    return () => clearInterval(id);
  }, [resendCooldown]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setMailUnavailable(false);
    setNoticeMessage("");

    try {
      const res = await forgotPassword(email);
      if (res && res.email_sent === false) {
        setMailUnavailable(true);
        setNoticeMessage(res.message || "Mail service is currently unavailable at the moment.");
        if (res.reset_url) {
          // Automatic fallback redirect after 2s if mail service fails
          const match = res.reset_url.match(/\/reset-password\/([^/]+)$/);
          if (match && match[1]) {
            setTimeout(() => {
              navigate(`/reset-password/${match[1]}`);
            }, 2500);
          }
        }
      }
    } catch {
      setMailUnavailable(true);
      setNoticeMessage("Mail service is currently unavailable at the moment.");
    } finally {
      setLoading(false);
      setSubmitted(true);
      setResendCooldown(60);
    }
  }

  async function handleResend() {
    if (resendCooldown > 0) return;
    setLoading(true);
    setMailUnavailable(false);
    try {
      const res = await forgotPassword(email);
      if (res && res.email_sent === false) {
        setMailUnavailable(true);
        setNoticeMessage(res.message || "Mail service is currently unavailable at the moment.");
      }
    } catch {
      setMailUnavailable(true);
      setNoticeMessage("Mail service is currently unavailable at the moment.");
    } finally {
      setLoading(false);
      setResendCooldown(60);
    }
  }

  if (submitted) {
    return (
      <div className="auth-form-box" id="forgot-password-success">
        <div className="success-state">
          {mailUnavailable ? (
            <div className="success-icon-circle" style={{ background: "rgba(245, 158, 11, 0.15)", color: "#f59e0b" }}>
              <AlertTriangle size={36} />
            </div>
          ) : (
            <div className="success-icon-circle">
              <CheckCircle size={36} />
            </div>
          )}
          <h1 className="success-title">{mailUnavailable ? "Mail Service Notice" : "Check your email"}</h1>
          <p className="success-desc">
            {mailUnavailable ? (
              <span style={{ color: "#d97706", fontWeight: 500 }}>
                {noticeMessage || "Mail service is currently unavailable at the moment."}
              </span>
            ) : (
              <>
                If an account exists for <strong>{email}</strong>, we sent a password
                reset link. The link expires in 5 minutes.
              </>
            )}
          </p>

          <div style={{ marginTop: 28, display: "flex", flexDirection: "column", gap: 10 }}>
            <button
              id="resend-email-btn"
              className="btn btn-secondary btn-full"
              onClick={handleResend}
              disabled={resendCooldown > 0 || loading}
            >
              {loading ? (
                <><span className="btn-spinner" /> Sending…</>
              ) : resendCooldown > 0 ? (
                <><RefreshCw size={14} /> Resend in {resendCooldown}s</>
              ) : (
                <><RefreshCw size={14} /> Resend email</>
              )}
            </button>

            <Link to="/login" id="back-to-login-from-success">
              <button className="btn btn-ghost btn-full">
                <ArrowLeft size={14} /> Back to login
              </button>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-form-box" id="forgot-password-form-container">
      <h1 className="auth-form-title">Reset your password</h1>
      <p className="auth-form-subtitle">
        Enter your email and we'll send you a reset link.
      </p>

      <form
        className="auth-form-fields"
        onSubmit={handleSubmit}
        style={{ marginTop: 32 }}
        noValidate
      >
        <div className="form-group">
          <label htmlFor="forgot-email" className="form-label">Email address</label>
          <div className="form-input-wrapper">
            <Mail
              size={15}
              style={{
                position: "absolute",
                left: 10,
                top: "50%",
                transform: "translateY(-50%)",
                color: "var(--text-secondary)",
              }}
            />
            <input
              id="forgot-email"
              type="email"
              className="form-input"
              style={{ paddingLeft: 32 }}
              placeholder="you@institution.ac.in"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoFocus
            />
          </div>
        </div>

        <button
          id="send-reset-link-btn"
          type="submit"
          className="btn btn-primary btn-full btn-lg"
          disabled={loading || !email}
        >
          {loading && <span className="btn-spinner" />}
          Send Reset Link
        </button>
      </form>

      <div className="auth-form-footer">
        <Link to="/login" id="back-to-login-link">
          <ArrowLeft size={13} style={{ display: "inline", marginRight: 4 }} />
          Back to login
        </Link>
      </div>
    </div>
  );
}
