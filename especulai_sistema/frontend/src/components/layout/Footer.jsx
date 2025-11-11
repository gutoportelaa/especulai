import { Link } from 'react-router-dom'
import logoEspeculai from '../../assets/solo_logo_Especulai.png'

export function Footer() {
  return (
    <footer className="w-full border-t bg-background/95 backdrop-blur-sm">
      <div className="container flex flex-col gap-8 px-4 py-10 md:px-6 lg:py-16">
        <div className="grid gap-8 sm:grid-cols-2 md:grid-cols-4">
          <div className="space-y-4">
            <div className="flex items-center gap-2 font-bold">
              <img 
                src={logoEspeculai} 
                alt="Especulai" 
                className="h-8 w-auto"
              />
              <span>Especulai</span>
            </div>
            <p className="text-sm text-muted-foreground">
              Plataforma inteligente de predição de preços imobiliários. 
              Obtenha estimativas precisas com tecnologia de ponta.
            </p>
          </div>
          
          <div className="space-y-4">
            <h4 className="text-sm font-bold">Produto</h4>
            <ul className="space-y-2 text-sm">
              <li>
                <a
                  href="/#features"
                  className="text-muted-foreground hover:text-foreground transition-colors"
                >
                  Recursos
                </a>
              </li>
              <li>
                <Link
                  to="/predict"
                  className="text-muted-foreground hover:text-foreground transition-colors"
                >
                  Predição
                </Link>
              </li>
              <li>
                <a
                  href="/#como-funciona"
                  className="text-muted-foreground hover:text-foreground transition-colors"
                >
                  Como Funciona
                </a>
              </li>
            </ul>
          </div>
          
          <div className="space-y-4">
            <h4 className="text-sm font-bold">Recursos</h4>
            <ul className="space-y-2 text-sm">
              <li>
                <a
                  href="/#faq"
                  className="text-muted-foreground hover:text-foreground transition-colors"
                >
                  FAQ
                </a>
              </li>
              <li>
                <a
                  href="#"
                  className="text-muted-foreground hover:text-foreground transition-colors"
                >
                  Documentação
                </a>
              </li>
              <li>
                <a
                  href="#"
                  className="text-muted-foreground hover:text-foreground transition-colors"
                >
                  Suporte
                </a>
              </li>
            </ul>
          </div>
          
          <div className="space-y-4">
            <h4 className="text-sm font-bold">Empresa</h4>
            <ul className="space-y-2 text-sm">
              <li>
                <a
                  href="#"
                  className="text-muted-foreground hover:text-foreground transition-colors"
                >
                  Sobre
                </a>
              </li>
              <li>
                <a
                  href="#"
                  className="text-muted-foreground hover:text-foreground transition-colors"
                >
                  Privacidade
                </a>
              </li>
              <li>
                <a
                  href="#"
                  className="text-muted-foreground hover:text-foreground transition-colors"
                >
                  Termos de Serviço
                </a>
              </li>
            </ul>
          </div>
        </div>
        
        <div className="flex flex-col gap-4 sm:flex-row justify-between items-center border-t border-border/40 pt-8">
          <p className="text-xs text-muted-foreground">
            &copy; {new Date().getFullYear()} Especulai. Todos os direitos reservados.
          </p>
          <div className="flex gap-4">
            <a
              href="#"
              className="text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              Privacidade
            </a>
            <a
              href="#"
              className="text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              Termos de Serviço
            </a>
          </div>
        </div>
      </div>
    </footer>
  )
}

