# 🌦️ WeatherSense AI — Smart IoT Weather Monitoring & ML Dashboard

**WeatherSense AI** is an intelligent, real-time weather analytics dashboard and predictive engine. It combines real-world REST API weather data with simulated edge IoT sensors, running client-side machine learning algorithms entirely in the browser using pure, vanilla JavaScript.

🌐 **Live Demo:** [View Deployed Project](https://dipali023.github.io/Weather-prediction-system-/)

---

## ✨ Features

### 📡 1. Hybrid Data & IoT Simulation
* **Live REST API Integration:** Fetches real-time 7-day weather forecasts and sunrise/sunset times from the free **Open-Meteo API** (no API key needed).
* **Multi-City Coordinates Engine:** Features an interactive location selector supporting popular Indian cities and states (Nagpur, Mumbai, Pune, Delhi, Bengaluru, Chennai, Kolkata, Hyderabad, Jaipur, Chandigarh, Patna, Guwahati, Srinagar, and Ahmedabad).
* **Edge Sensor Simulation:** Models an IoT weather station node (simulating an ESP8266 microcontroller paired with DHT22, BMP280, and ML8511 sensors) which generates fluctuating live readings (temperature, humidity, sea-level pressure, altitude, wind speed, gust, direction, rain gauge intensity, and UV index) anchored directly to the selected city's actual live API baseline.

### 🤖 2. In-Browser Machine Learning (From Scratch)
* **Linear Regression Predictor:** Trains on live local sensor history to forecast temperature trends (1h, 2h, and 3h ahead) in real-time, calculating and displaying current model accuracy metrics ($R^2$ coefficient of determination and Root Mean Squared Error - RMSE).
* **Random Forest Classifier:** Employs an internal decision forest model (15 logic trees) to evaluate incoming multi-variate sensor logs and classify atmospheric states (e.g., *Heat Index Warning*, *Squally*, *Monsoon*, *Muggy*, *Heavy Rain*) and calculate rain probability.

### 📊 3. Statistical Anomaly Detection & Health Advisories
* **Z-Score Anomaly Detector:** Monitors incoming temperature and humidity streams using standard deviation thresholding to identify sensor spikes, errors, or environmental anomalies.
* **Health Advisory Engine:** Evaluates live metrics (heat index, humidity, UV levels) to yield a dynamic Wellness Index (0-100) along with targeted health tips (e.g., hydration guidance, sunscreen warnings, wind warnings).

### 🎨 4. Premium Responsive UI/UX
* Designed with a cutting-edge **glassmorphic dark UI** featuring custom blurred glass panels and subtle particle physics.
* Dynamic **Aurora Borealis background glows** powered by floating CSS radial gradients.
* Real-time charting powered by **Chart.js** displaying live sparklines, scatter regression plots, and multivariate timelines.
* Fully responsive layout (desktop, tablet, and mobile browsers).

---

## 🛠️ Technology Stack

* **Frontend:** HTML5, Vanilla CSS3 (Custom design tokens, flexbox/grid layout), JavaScript (ES6+).
* **Charts/Visualization:** [Chart.js](https://www.chartjs.org/) (UMD via CDN).
* **Data Sources:** [Open-Meteo REST API](https://open-meteo.com/).
* **Local Hosting:** Node.js (via `http-server`).

---

## 🚀 How to Run Locally

Since this dashboard runs entirely client-side, you don't need a heavy backend setup. You can run it locally with any simple static web server:

### Prerequisite
Ensure you have [Node.js](https://nodejs.org/) installed.

### Steps:
1. Clone the repository:
   ```bash
   git clone https://github.com/dipali023/Weather-prediction-system-.git
   cd Weather-prediction-system-
   ```
2. Start the local server:
   ```bash
   npx http-server -p 8000
   ```
3. Open your browser and navigate to:
   ```
   http://localhost:8000
   ```

---

## 🧠 Behind the Algorithms

### Client-Side Linear Regression
The regression engine uses the least-squares method to calculate the line of best fit over the historical sliding-window sensor readings.
* **Slope ($m$) & Intercept ($c$):**
  $$m = \frac{\sum(x - \bar{x})(y - \bar{y})}{\sum(x - \bar{x})^2}$$
  $$c = \bar{y} - m\bar{x}$$
* **Evaluation:** Calculates $R^2$ dynamically to inform the dashboard user of prediction confidence based on current variance.

### Decision-Tree Forest Logic
The random forest mimics a group of classified decision boundaries trained on typical climate profiles. The final condition displayed represents the mode (majority vote) computed across 15 trees evaluating different criteria branches.
