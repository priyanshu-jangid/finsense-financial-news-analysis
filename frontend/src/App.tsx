import FeedPage from './pages/FeedPage';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { AppLayout } from './components/AppLayout';
import Dashboard from './pages/Dashboard';
import NewsPage from './pages/NewsPage';
import WatchlistPage from './pages/WatchlistPage';
import CompanyDetailPage from './pages/CompanyDetailPage';
import Login from './pages/Login';
import Register from './pages/Register';
import './App.css';

function App() {
  return (
    <AuthProvider>
      <Router>
        <AppLayout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/news" element={<NewsPage />} />
            <Route path="/watchlist" element={<WatchlistPage />} />
            <Route path="/company/:id" element={<CompanyDetailPage />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="*" element={<Navigate to="/" replace />} />
	    <Route path="/feed" element={<FeedPage />} />
          </Routes>
        </AppLayout>
      </Router>
    </AuthProvider>
  );
}

export default App;
