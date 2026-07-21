import { render, screen, cleanup } from '@testing-library/react'
import userEvent from '@testing-library/user-effect'
import { LoginForm } from '../src/components/LoginForm'

describe('LoginForm', () => {
  afterEach(() => {
    cleanup()
  })

  it('renders email and password inputs and submit button', () => {
    render(<LoginForm />)

    const emailInput = screen.getByLabelText(/email/i)
    const passwordInput = screen.getByLabelText(/password/i)
    const submitButton = screen.getByRole('button', { name: /sign in/i })

    expect(emailInput).toBeInTheDocument()
    expect(passwordInput).toBeInTheDocument()
    expect(submitButton).toBeInTheDocument()
  })

  it('shows error message for invalid email', async () => {
    render(<LoginForm />)

    const emailInput = screen.getByLabelText(/email/i)
    const passwordInput = screen.getByLabelText(/password/i)
    const submitButton = screen.getByRole('button', { name: /sign in/i })

    await userEvent.type(emailInput, 'invalid-email')
    await userEvent.type(passwordInput, 'password123')
    await userEvent.click(submitButton)

    const errorMessage = screen.getByText(/invalid email/i)
    expect(errorMessage).toBeInTheDocument()
  })

  it('shows error message for short password', async () => {
    render(<LoginForm />)

    const emailInput = screen.getByLabelText(/email/i)
    const passwordInput = screen.getByLabelText(/password/i)
    const submitButton = screen.getByRole('button', { name: /sign in/i })

    await userEvent.type(emailInput, 'valid@example.com')
    await userEvent.type(passwordInput, '123')
    await userEvent.click(submitButton)

    const errorMessage = screen.getByText(/password too short/i)
    expect(errorMessage).toBeInTheDocument()
  })

  it('calls onLogin with valid credentials', async () => {
    const onLogin = jest.fn()
    render(<LoginForm onLogin={onLogin} />)

    const emailInput = screen.getByLabelText(/email/i)
    const passwordInput = screen.getByLabelText(/password/i)
    const submitButton = screen.getByRole('button', { name: /sign in/i })

    await userEvent.type(emailInput, 'valid@example.com')
    await userEvent.type(passwordInput, 'password123')
    await userEvent.click(submitButton)

    expect(onLogin).toHaveBeenCalledWith({
      email: 'valid@example.com',
      password: 'password123'
    })
  })
})