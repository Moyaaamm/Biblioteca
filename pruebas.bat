@echo off
echo Creando Usuario...
curl -X POST "http://localhost:8000/api/v1/usuarios/usuarios" -H "Content-Type: application/json" -d "{\"nombre\":\"Estudiante 1\",\"email\":\"estudiante@test.com\"}"
echo.

echo Creando Libro...
curl -X POST "http://localhost:8000/api/v1/libros/libros" -H "Content-Type: application/json" -d "{\"titulo\":\"SOA Book\",\"autor\":\"Autor X\"}"
echo.

echo Orquestando Prestamo...
curl -X POST "http://localhost:8000/api/v1/prestamos/prestamos" -H "Content-Type: application/json" -d "{\"usuario_id\":1,\"libro_id\":1}"
echo.

echo Consultando Catalogo de Libros a traves del Gateway...
curl -X GET "http://localhost:8000/api/v1/libros/libros"
echo.
pause