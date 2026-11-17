"""Gestor de tareas en la terminal."""


def add(title: str, tasks: list[str]) -> list[str]:
    """Añade una tarea al final de la lista.

    Args:
        title: Título de la tarea; no puede estar vacío.
        tasks: Lista actual de tareas.

    Returns:
        Una lista nueva con la tarea añadida.

    Raises:
        ValueError: Si el título está vacío.
    """
    if not title.strip():
        raise ValueError("El título no puede estar vacío.")
    return [*tasks, title.strip()]


def main() -> None:
    """Punto de entrada de la CLI."""
    print("tareas-cli")
