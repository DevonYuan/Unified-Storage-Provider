import React from 'react';
import { useForm } from 'react-hook-form';
import { useNavigate, Link } from 'react-router-dom';
import { authService } from '../api/auth.service';
import { useAuth } from '../context/AuthContext';

const Login: React.FC = () => {
    const { signIn } = useAuth();
    const navigate = useNavigate();
    const { register, handleSubmit, formState: { errors }, setValue } = useForm({
        defaultValues: {
            email: '',
            password: '',
        },
    });

    const onSubmit = async (data: any) => {
        try {
            const result = await authService.login(data.email, data.password);
            signIn(result.access_token, result.user);
            navigate('/dashboard');
        } catch (error: any) {
            alert(error.response?.data?.detail || 'Login failed');
        }
    };

    return (
        <div className="auth-container">
            <h2>Login</h2>
            <form onSubmit={handleSubmit(onSubmit)}>
                <div className="form-group">
                    <label htmlFor="email">Email</label>
                    <input
                        id="email"
                        type="email"
                        {...register('email', { required: 'Email is required', pattern: { value: /^\S+@\S+$/, message: 'Invalid email format' } })}
                        className="form-input"
                    />
                    {errors.email && <span className="error-message">{errors.email.message as string}</span>}
                </div>
                <div className="form-group">
                    <label htmlFor="password">Password</label>
                    <input
                        id="password"
                        type="password"
                        {...register('password', { required: 'Password is required' })}
                        className="form-input"
                    />
                    {errors.password && <span className="error-message">{errors.password.message as string}</span>}
                </div>
                <button type="submit" className="btn-primary w-full">Sign In</button>
                <p className="text-center mt-4">
                    Don't have an account? <Link to="/register">Sign up</Link>
                </p>
            </form>
        </div>
    );
};

export default Login;
