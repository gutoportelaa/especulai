import { useState } from 'react'

export function useMobileMenu() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  const toggleMenu = () => {
    setMobileMenuOpen(prev => !prev)
  }

  const closeMenu = () => {
    setMobileMenuOpen(false)
  }

  return {
    mobileMenuOpen,
    toggleMenu,
    closeMenu
  }
}

