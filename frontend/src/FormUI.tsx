import type { ReactNode } from 'react';
import { X } from 'lucide-react';

export function Field({label,children,wide=false}: {label:string,children:ReactNode,wide?:boolean}) {
  return <label className={`field ${wide?'wide':''}`}><span>{label}</span>{children}</label>;
}
export function Modal({title,subtitle,children,close,wide=false}: {title:string,subtitle?:string,children:ReactNode,close:()=>void,wide?:boolean}) {
  return <div className="overlay" onMouseDown={e=>{if(e.target===e.currentTarget)close();}}><section className={`modal ${wide?'large':''}`} role="dialog" aria-modal="true" aria-label={title}><header><div><h2>{title}</h2>{subtitle&&<p>{subtitle}</p>}</div><button className="icon-button" onClick={close} aria-label="Close dialog"><X size={21}/></button></header>{children}</section></div>;
}
