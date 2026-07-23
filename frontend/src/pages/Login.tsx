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
        <div style={{ maxWidth: '400px', margin: '2rem auto', padding: '1rem', border: '1px solid #ccc', borderRadius: '8px' }}>
            <h2>Login</h2>
            <form onSubmit={handleSubmit(onSubmit)}>
                <div style={{ marginBottom: '1rem' }}>
                    <label htmlFor="email">Email</label><br/>
                    <input
                        id="email"
                        {...register('email', { required: 'Email is required', pattern: { value: /^\S+@\S+$/, message: 'Invalid email format' } })}
                        style={{ width: '100%' }}
                    />
                    {errors.email && <span style={{ color: 'red', fontSize: '0.8rem' }}>{errors.email.message as string}</span>}
                </div>
                <div style={{ marginBottom: '1rem' }}>
                    <label htmlFor="password">Password</label><br/>
                    <input
                        id="password"
                        type="password"
                        {...register('password', { required: 'Password is required' })}
                        style={{ width: '100%' }}
                    />
                    {errors.password && <span style={{ color: 'red', fontSize: '0.8rem' }}>{errors.password.message as string}</span>}
                </div>
                <button type="submit" style={{ width: '100%', padding: '0.5rem', marginBottom: '0.5rem' }}>Sign In</button>
                <p style={{ textAlign: 'center' }}>
                    Don't have an account? <Link to="/register">Sign up</Link>
                </p>
            </form>
        </div>
    );
};

export default Login;
