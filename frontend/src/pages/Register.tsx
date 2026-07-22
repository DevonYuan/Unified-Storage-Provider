import React from 'react';
import { useForm } from 'react-hook-form';
import { useNavigate } from 'react-router-dom';
import { authService } from '../api/auth.service';

const Register: React.FC = () => {
    const navigate = useNavigate();
    const { register, handleSubmit, formState: { errors } } = useForm({
        defaultValues: {
            email: '',
            password: '',
            confirmPassword: '',
        },
    });

    const onSubmit = async (data: any) => {
        try {
            await authService.register(data.email, data.password);
            alert('Registration successful! Please check your email to verify your account.');
            navigate('/login');
        } catch (error: any) {
            alert(error.response?.data?.detail || 'Registration failed');
        }
    };

    return (
        <div style={{ maxWidth: '400px', margin: '2rem auto', padding: '1rem', border: '1px solid #ccc', borderRadius: '8px' }}>
            <h2>Register</h2>
            <form onSubmit={handleSubmit(onSubmit)}>
                <div style={{ marginBottom: '1rem' }}>
                    <label htmlFor="email">Email</label><br/>
                    <input
                        id="email"
                        {...register('email', {
                            required: 'Email is required',
                            pattern: { value: /^\S+@\S+$/, message: 'Invalid email format' }
                        })}
                        style={{ width: '100%' }}
                    />
                    {errors.email && <span style={{ color: 'red', fontSize: '0.8rem' }}>{errors.email.message as string}</span>}
                </div>
                <div style={{ marginBottom: '1rem' }}>
                    <label htmlFor="password">Password</label><br/>
                    <input
                        id="password"
                        type="password"
                        {...register('password', {
                            required: 'Password is required',
                            minLength: { value: 8, message: 'Password must be at least 8 characters long' }
                        })}
                        style={{ width: '100%' }}
                    />
                    {errors.password && <span style={{ color: 'red', fontSize: '0.8rem' }}>{errors.password.message as string}</span>}
                </div>
                <div style={{ marginBottom: '1rem' }}>
                    <label htmlFor="confirmPassword">Confirm Password</label><br/>
                    <input
                        id="confirmPassword"
                        type="password"
                        {...register('confirmPassword', {
                            required: 'Confirmation is required',
                            validate: (value, formValues) => value === formValues.password || 'Passwords do not match'
                        })}
                        style={{ width: '100%' }}
                    />
                    {errors.confirmPassword && <span style={{ color: 'red', fontSize: '0.8rem' }}>{errors.confirmPassword.message as string}</span>}
                </div>
                <button type="submit" style={{ width: '100%', padding: '0.5rem' }}>Register</button>
            </form>
        </div>
    );
};

export default Register;
