import * as React from "react"
import { ChevronDown } from "lucide-react"
import { cn } from "../../lib/utils"

const AccordionContext = React.createContext({
  value: null,
  onValueChange: () => {},
})

const Accordion = ({ type = "single", collapsible = true, className, children, ...props }) => {
  const [value, setValue] = React.useState(null)

  const onValueChange = React.useCallback((newValue) => {
    if (type === "single") {
      setValue((prev) => (prev === newValue && collapsible ? null : newValue))
    }
  }, [type, collapsible])

  return (
    <AccordionContext.Provider value={{ value, onValueChange }}>
      <div className={cn("w-full", className)} {...props}>
        {children}
      </div>
    </AccordionContext.Provider>
  )
}

const AccordionItem = React.forwardRef(({ className, value: itemValue, ...props }, ref) => {
  return (
    <div
      ref={ref}
      className={cn("border-b", className)}
      {...props}
    />
  )
})
AccordionItem.displayName = "AccordionItem"

const AccordionTrigger = React.forwardRef(({ className, children, value: itemValue, ...props }, ref) => {
  const { value, onValueChange } = React.useContext(AccordionContext)
  const isOpen = value === itemValue

  return (
    <button
      ref={ref}
      type="button"
      className={cn(
        "flex flex-1 items-center justify-between py-4 font-medium transition-all hover:underline [&[data-state=open]>svg]:rotate-180",
        className
      )}
      onClick={() => onValueChange(itemValue)}
      data-state={isOpen ? "open" : "closed"}
      {...props}
    >
      {children}
      <ChevronDown className="h-4 w-4 shrink-0 transition-transform duration-200" />
    </button>
  )
})
AccordionTrigger.displayName = "AccordionTrigger"

const AccordionContent = React.forwardRef(({ className, children, value: itemValue, ...props }, ref) => {
  const { value } = React.useContext(AccordionContext)
  const isOpen = value === itemValue
  const [height, setHeight] = React.useState(0)
  const contentRef = React.useRef(null)

  React.useEffect(() => {
    if (contentRef.current) {
      setHeight(isOpen ? contentRef.current.scrollHeight : 0)
    }
  }, [isOpen])

  return (
    <div
      ref={ref}
      className={cn(
        "overflow-hidden text-sm transition-all duration-200 ease-out",
        isOpen ? "" : ""
      )}
      style={{ height: `${height}px` }}
      data-state={isOpen ? "open" : "closed"}
      {...props}
    >
      <div ref={contentRef} className={cn("pb-4 pt-0", className)}>
        {children}
      </div>
    </div>
  )
})
AccordionContent.displayName = "AccordionContent"

export { Accordion, AccordionItem, AccordionTrigger, AccordionContent }

