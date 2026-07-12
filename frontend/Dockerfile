FROM node:18-slim

WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Expose Vite dev server port
EXPOSE 5173

# We use the Vite dev server for the local demo to easily proxy the API requests
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
