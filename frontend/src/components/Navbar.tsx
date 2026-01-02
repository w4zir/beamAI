import { Link, useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { supabase } from '../api/supabase'

export default function Navbar() {
  const navigate = useNavigate()
  const [email, setEmail] = useState<string | null>(null)

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setEmail(data.session?.user?.email ?? null)
    })
    const { data: sub } = supabase.auth.onAuthStateChange((_event, session) => {
      setEmail(session?.user?.email ?? null)
      // Redirect to login if signed out
      if (!session) {
        navigate('/login')
      }
    })
    return () => { sub.subscription.unsubscribe() }
  }, [navigate])

  async function handleSignOut() {
    await supabase.auth.signOut()
    navigate('/login')
  }

  if (!email) {
    return null // Don't show navbar if not authenticated
  }

  return (
    <nav className="p-4 flex gap-4 items-center border-b bg-white shadow-sm">
      <Link to="/dashboard" className="font-bold text-xl text-blue-600 hover:text-blue-700">
        BeamAI
      </Link>
      <div className="flex gap-4 ml-6">
        <Link 
          to="/search" 
          className="text-gray-700 hover:text-blue-600 font-medium text-sm hover:underline"
        >
          Search
        </Link>
        <Link 
          to="/recommendations" 
          className="text-gray-700 hover:text-blue-600 font-medium text-sm hover:underline"
        >
          Recommendations
        </Link>
      </div>
      <div className="ml-auto flex items-center gap-4">
        <span className="text-sm text-gray-600 hidden sm:inline">{email}</span>
        <button 
          onClick={handleSignOut} 
          className="text-blue-600 hover:text-blue-800 font-medium text-sm hover:underline"
        >
          Sign Out
        </button>
      </div>
    </nav>
  )
}


