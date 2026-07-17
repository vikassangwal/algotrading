FROM node:20-alpine

WORKDIR /app

# Install deps first for layer caching (.dockerignore excludes node_modules)
COPY package*.json ./
RUN npm install

# Copy source and build the production bundle
COPY . .
RUN npm run build

EXPOSE 3000

# Serve the built dist/ on port 3000 (vite.config.js sets host+port)
CMD ["npm", "run", "preview"]
