# Use an official Node.js runtime as a parent image
FROM node:14

# Set the working directory in the container
WORKDIR /front_end/audio-visualizer

# Copy the package.json and package-lock.json files
COPY package*.json ./

# Install any needed packages
RUN npm install

# Copy the current directory contents into the container at /app
COPY . .

# Build the app for production
RUN npm install selfsigned
RUN npm run build
# Install serve to serve the build files
RUN npm install -g serve

# Make port 3000 available to the world outside this container
EXPOSE 3000

# Serve the build files
CMD ["serve", "-s", "build", "-l", "3000"]