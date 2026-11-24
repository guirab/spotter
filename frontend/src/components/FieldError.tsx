type Props = { id: string; message?: string }

/** An API validation error under its field; point the field's `aria-describedby` at `id`. */
export function FieldError({ id, message }: Props) {
  return message ? (
    <p id={id} className="text-sm text-destructive">
      {message}
    </p>
  ) : null
}
