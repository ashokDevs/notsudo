#!/bin/bash

cd backend && python app.py &

cd frontend && npm run dev
