import { Link } from "react-router-dom";

interface LogoProps {
  path?: string;
  className?: string;
  fontSize?: string;
  color?: string;
  textShadow?: string;
}

const Logo = ({ 
  path = "/", 
  className = "", 
  fontSize = "1.5rem", 
  textShadow = "none" 
}: LogoProps) => {
  return (
    <Link 
      to={path} 
      className={className} 
      style={{
        fontFamily: 'var(--font-pixel)',
        fontSize: fontSize,
        color: 'var(--yellow)',
        textDecoration: 'none',
        textShadow: textShadow,
        flexShrink: 0,
        fontWeight: '800',
        letterSpacing: '2px',    
      }}
    >
      Serene.AI
    </Link>
  );
};

export default Logo;