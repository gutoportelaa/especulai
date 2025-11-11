import { Link } from 'react-router-dom'
import { Menu, X } from 'lucide-react'
import { Button } from '../ui/button'
import { useScroll } from '../../hooks/useScroll'
import { useMobileMenu } from '../../hooks/useMobileMenu'
import { motion, AnimatePresence } from 'framer-motion'
import logoEspeculai from '../../assets/solo_logo_Especulai.png'

export function Header() {
  const isScrolled = useScroll()
  const { mobileMenuOpen, toggleMenu, closeMenu } = useMobileMenu()

  return (
    <header
      className={`sticky top-0 z-50 w-full backdrop-blur-lg transition-all duration-300 ${
        isScrolled ? 'bg-background/80 shadow-sm' : 'bg-transparent'
      }`}
    >
      <div className="container flex h-16 items-center justify-between">
        <Link to="/" className="flex items-center gap-2 font-bold">
          <img 
            src={logoEspeculai} 
            alt="Especulai" 
            className="h-8 w-auto"
          />
          <span className="text-xl">Especulai</span>
        </Link>
        
        <nav className="hidden md:flex gap-8">
          <a
            href="/#features"
            className="text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
          >
            Recursos
          </a>
          <a
            href="/#como-funciona"
            className="text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
          >
            Como Funciona
          </a>
          <a
            href="/#faq"
            className="text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
          >
            FAQ
          </a>
        </nav>
        
        <div className="hidden md:flex gap-4 items-center">
          <Link to="/predict">
            <Button className="rounded-full">
              Fazer Predição
            </Button>
          </Link>
        </div>
        
        <div className="flex items-center gap-4 md:hidden">
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleMenu}
            className="rounded-full"
          >
            {mobileMenuOpen ? <X className="size-5" /> : <Menu className="size-5" />}
            <span className="sr-only">Toggle menu</span>
          </Button>
        </div>
      </div>
      
      {/* Mobile menu */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="md:hidden absolute top-16 inset-x-0 bg-background/95 backdrop-blur-lg border-b"
          >
            <div className="container py-4 flex flex-col gap-4">
              <a
                href="/#features"
                className="py-2 text-sm font-medium"
                onClick={closeMenu}
              >
                Recursos
              </a>
              <a
                href="/#como-funciona"
                className="py-2 text-sm font-medium"
                onClick={closeMenu}
              >
                Como Funciona
              </a>
              <a
                href="/#faq"
                className="py-2 text-sm font-medium"
                onClick={closeMenu}
              >
                FAQ
              </a>
              <div className="flex flex-col gap-2 pt-2 border-t">
                <Link to="/predict" onClick={closeMenu}>
                  <Button className="rounded-full w-full">
                    Fazer Predição
                  </Button>
                </Link>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  )
}

