import mock_page from '../assets/get_results.png';
import { useNavigate } from 'react-router-dom';


const RecommendationsPage = () => {
    const navigate = useNavigate();
    return (
        <div>
            <img src={mock_page} alt="mock_page"  onClick={() => navigate('/apartment-swipe')}/>
        </div>
    )
}

export default RecommendationsPage;