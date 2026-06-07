import React from "react";

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error) {
    console.error("UI error:", error);
  }

  render() {
    if (this.state.hasError) {
      return (
        <main className="auth-page">
          <div className="auth-card">
            <h1>Something went wrong in the UI.</h1>
            <button className="primary-button" onClick={() => window.location.reload()}>Reload Page</button>
          </div>
        </main>
      );
    }
    return this.props.children;
  }
}

