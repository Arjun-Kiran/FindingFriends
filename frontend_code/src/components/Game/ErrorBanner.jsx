const ErrorBanner = ({ message, onDismiss }) => {
    if (!message) return null;

    return (
        <div className="info-panel error">
            <span>{message}</span>
            <button className="close-btn" onClick={onDismiss}>✕</button>
        </div>
    );
};

export default ErrorBanner;
