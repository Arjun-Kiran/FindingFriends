import { Icon } from '../Emoji';
import { STATUS_EMOJI } from '../../constants/emoji';

const ErrorBanner = ({ message, onDismiss }) => {
    if (!message) return null;

    return (
        <div className="info-panel error">
            <span><Icon emoji={STATUS_EMOJI.ERROR} label="Error" />{message}</span>
            <button className="close-btn" onClick={onDismiss}>✕</button>
        </div>
    );
};

export default ErrorBanner;
