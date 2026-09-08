# FindBack AI — convenience dev commands.
# Run `make help` to see all targets.

.PHONY: help backend frontend backend-test frontend-build

help:
	@echo "make backend         # bootstrap + run FastAPI on :8000"
	@echo "make frontend        # bootstrap + run Next.js on :3000"
	@echo "make backend-test    # run backend pytest suite"
	@echo "make frontend-build  # production build check for the frontend"

backend:
	chmod +x backend/scripts/dev.sh
	./backend/scripts/dev.sh

frontend:
	chmod +x frontend/scripts/dev.sh
	./frontend/scripts/dev.sh

backend-test:
	cd backend && . .venv/bin/activate && pytest -q

frontend-build:
	cd frontend && npm install && npm run build
