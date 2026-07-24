import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { useNavigate, Link } from 'react-router-dom';
import { authService } from '../api/auth.service';

const Register: React.FC = () => {
    const navigate = useNavigate();
    const [successMessage, setSuccessMessage] = useState('');
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
            setSuccessMessage('Registration successful! A verification link has been sent to your email address.');
        } catch (error: any) {
            alert(error.response?.data?.detail || 'Registration failed');
        }
    };

    return (
        <div className="auth-container">
            <h2>Register</h2>
            <form onSubmit={handleSubmit(onSubmit)}>
                <div className="form-group">
                    <label htmlFor="email">Email</label>
                    <input
                        id="email"
                        type="email"
                        {...register('email', {
                            required: 'Email is required',
                            pattern: { value: /^\S+@\S+$/, message: 'Invalid email format' }
                        })}
                        className="form-input"
                    />
                    {errors.email && <span className="error-message">{errors.email.message as string}</span>}
                </div>
                <div className="form-group">
                    <label htmlFor="password">Password</label>
                    <input
                        id="password"
                        type="password"
                        {...register('password', {
                            required: 'Password is required',
                            minLength: { value: 8, message: 'Password must be at least 8 characters long' }
                        })}
                        className="form-input"
                    />
                    {errors.password && <span className="error-message">{errors.password.message as string}</span>}
                </div>
                <div className="form-group">
                    <label htmlFor="confirmPassword">Confirm Password</label>
                    <input
                        id="confirmPassword"
                        type="password"
                        {...register('confirmPassword', {
                            required: 'Confirmation is required',
                            validate: (value, formValues) => value === formValues.password || 'Passwords do not match'
                        })}
                        className="form-input"
                    />
                    {errors.confirmPassword && <span className="error-message">{errors.confirmPassword.message as string}</span>}
                </div>
                {successMessage && (
                    <p className="success-message">{successMessage}</p>
                )}
                <button type="submit" className="btn-primary w-full">Register</button>
                <p className="text-center mt-4">
                    Already have an account? <Link to="/login">Log in</Link>
                </p>
            </form>
        </div>
    );
};

export default Register;
