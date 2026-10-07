@echo off
curl -X POST http://localhost:8002/usuarios -H "Content-Type: application/json" -d "{\"nombre\":\"Ana Lopez\",\"email\":\"ana@example.com\"}"
curl -X POST http://localhost:8001/libros -H "Content-Type: application/json" -d "{\"titulo\":\"Cien anos de soledad\",\"autor\":\"Gabriel Garcia Marquez\"}"
curl -X POST http://localhost:8003/prestamos -H "Content-Type: application/json" -d "{\"usuario_id\":1,\"libro_id\":1}"
curl http://localhost:8003/prestamos
curl -X PATCH http://localhost:8003/prestamos/1/devolver
curl http://localhost:8001/libros
