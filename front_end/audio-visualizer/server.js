const express = require('express');
const cors = require('cors');
const path = require('path');
const axios = require('axios'); // To make requests to Flask backend
const app = express();
const port = 3000;

// Middleware to parse JSON data
app.use(express.json());

// Enable CORS for all routes
app.use(cors());

// Serve static files from the React app
app.use(express.static(path.join(__dirname, 'build')));

// Proxy POST requests for audio and image upload to Flask
app.post('/audio_image', async (req, res) => {
  try {
    const formData = new FormData();
    formData.append('audio', req.files.audio);
    formData.append('image', req.files.image);

    const response = await axios.post('http://localhost:5000/audio_image', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });

    res.json(response.data);
  } catch (error) {
    console.error('Error proxying request:', error);
    res.status(500).json({ message: 'Error proxying request' });
  }
});

// Handle all other routes and serve the index.html file
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'build', 'index.html'));
});

// Start the server
app.listen(port, () => {
  console.log(`Server is running at http://localhost:${port}`);
});