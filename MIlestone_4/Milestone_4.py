import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from statsmodels.tsa.arima.model import ARIMA
import tkinter as tk
from tkinter import ttk
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s',
                    handlers=[
                        logging.FileHandler("ERP_Integration.log"),
                        logging.FileHandler("Disruption_Modeling.log"),
                        logging.StreamHandler()
                    ])

# Slack and Email Configurations
SLACK_WEBHOOK_URL = 'https://hooks.slack.com/services/your/webhook/url'  # Replace with your Slack Webhook URL
SENDER_EMAIL = "your-email@example.com"  # Replace with your email
RECEIVER_EMAIL = "receiver-email@example.com"  # Replace with the receiver's email
SMTP_SERVER = "smtp.example.com"  # Replace with your SMTP server
SMTP_PORT = 587  # SMTP server port (usually 587 for TLS)
SMTP_PASSWORD = "your-email-password"  # Replace with your email password


class InventoryAnalyzer:
    def __init__(self):
        self.create_sample_data()

    def create_sample_data(self):
        """Create sample inventory data for demonstration"""
        dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
        np.random.seed(42)
        self.inventory_data = pd.DataFrame({
            'date': dates.repeat(3),
            'product_id': ['P001', 'P002', 'P003'] * len(dates),
            'quantity': np.random.randint(10, 100, len(dates) * 3),
            'transaction_type': np.random.choice(['in', 'out'], len(dates) * 3),
            'unit_price': np.random.uniform(10, 100, len(dates) * 3).round(2)
        })
        self.product_info = pd.DataFrame({
            'product_id': ['P001', 'P002', 'P003'],
            'product_name': ['Widgets', 'Gadgets', 'Tools'],
            'category': ['Electronics', 'Electronics', 'Hardware'],
            'min_stock': [20, 15, 25],
            'max_stock': [80, 70, 90]
        })

    def calculate_current_stock(self):
        """Calculate current stock levels for each product"""
        stock_movement = self.inventory_data.groupby(
            ['product_id', 'transaction_type'])['quantity'].sum().unstack(fill_value=0)
        current_stock = pd.DataFrame({
            'current_stock': stock_movement['in'] - stock_movement['out']
        }).reset_index()
        return current_stock.merge(self.product_info, on='product_id')

    def forecast_disruption(self, product_id, steps=30):
        """Forecast inventory levels using ARIMA"""
        product_data = self.inventory_data[self.inventory_data['product_id'] == product_id]
        product_data = product_data.groupby('date')['quantity'].sum()
        model = ARIMA(product_data, order=(1, 1, 1))
        model_fit = model.fit()
        forecast = model_fit.forecast(steps=steps)
        return forecast

    def simulate_erp_integration(self, current_stock):
        """Simulate ERP integration and suggest stock adjustments"""
        recommendations = current_stock[current_stock['current_stock'] < current_stock['min_stock']]
        recommendations['recommended_order'] = (
            recommendations['max_stock'] - recommendations['current_stock']
        )
        logging.info("ERP Recommendations:")
        logging.info(recommendations[['product_id', 'product_name', 'recommended_order']])
        return recommendations

    def generate_disruption_analysis(self, product_id):
        """Analyze disruption risks for a given product"""
        forecast = self.forecast_disruption(product_id)
        min_stock = self.product_info[self.product_info['product_id'] == product_id]['min_stock'].values[0]
        risk = (forecast < min_stock).mean() * 100  # Percentage of days below min_stock
        disruption_analysis = {
            'product_id': product_id,
            'risk_percentage': risk,
            'forecasted_values': forecast
        }
        logging.info("Disruption Analysis:")
        logging.info(disruption_analysis)
        return disruption_analysis

    def send_slack_notification(self, message):
        """Send real-time Slack notification"""
        payload = {'text': message}
        requests.post(SLACK_WEBHOOK_URL, json=payload)

    def send_email_notification(self, subject, body):
        """Send email notification"""
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECEIVER_EMAIL
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SMTP_PASSWORD)
            text = msg.as_string()
            server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, text)

    def plot_inventory_status(self, current_stock):
        """Plot inventory status"""
        fig = make_subplots(rows=1, cols=1)
        for product_id in current_stock['product_id'].unique():
            product_data = current_stock[current_stock['product_id'] == product_id]
            fig.add_trace(go.Bar(
                x=product_data['product_name'],
                y=product_data['current_stock'],
                name=product_id
            ))
        fig.update_layout(title="Current Inventory Status", xaxis_title="Product", yaxis_title="Current Stock")
        fig.show()

    def plot_forecasted_disruption(self, product_id, forecast):
        """Plot forecasted disruption levels"""
        plt.plot(range(len(forecast)), forecast)
        plt.title(f"Disruption Forecast for {product_id}")
        plt.xlabel('Days')
        plt.ylabel('Forecasted Inventory')
        plt.show()


class InventoryApp:
    def __init__(self, root, analyzer):
        self.analyzer = analyzer
        self.root = root
        self.root.title("Inventory Management System")
        self.create_widgets()

    def create_widgets(self):
        ttk.Label(self.root, text="Inventory Management System", font=("Arial", 16)).grid(row=0, column=0, columnspan=2, pady=10)

        ttk.Button(self.root, text="View Current Stock", command=self.view_stock).grid(row=1, column=0, pady=5)
        ttk.Button(self.root, text="Simulate ERP Integration", command=self.erp_integration).grid(row=2, column=0, pady=5)
        ttk.Button(self.root, text="Analyze Disruption", command=self.analyze_disruption).grid(row=3, column=0, pady=5)

        self.output = tk.Text(self.root, width=80, height=20, wrap=tk.WORD)
        self.output.grid(row=1, column=1, rowspan=3, padx=10, pady=5)

    def view_stock(self):
        current_stock = self.analyzer.calculate_current_stock()
        self.output.delete(1.0, tk.END)
        self.output.insert(tk.END, current_stock.to_string(index=False))
        self.analyzer.plot_inventory_status(current_stock)

    def erp_integration(self):
        current_stock = self.analyzer.calculate_current_stock()
        recommendations = self.analyzer.simulate_erp_integration(current_stock)
        self.output.delete(1.0, tk.END)
        self.output.insert(tk.END, recommendations.to_string(index=False))

        # Send Slack notification
        self.analyzer.send_slack_notification(f"ERP Recommendations: {recommendations.to_string(index=False)}")

        # Send Email notification
        self.analyzer.send_email_notification("ERP Recommendations", recommendations.to_string(index=False))

    def analyze_disruption(self):
        product_id = 'P001'  # Example product
        analysis = self.analyzer.generate_disruption_analysis(product_id)
        self.output.delete(1.0, tk.END)
        self.output.insert(tk.END, f"Product: {product_id}\nRisk Percentage: {analysis['risk_percentage']}%\nForecasted Values:\n{analysis['forecasted_values']}")

        # Plot forecasted disruption
        self.analyzer.plot_forecasted_disruption(product_id, analysis['forecasted_values'])

        # Send Slack notification
        self.analyzer.send_slack_notification(f"Disruption Analysis: Risk Percentage: {analysis['risk_percentage']}%")

        # Send Email notification
        self.analyzer.send_email_notification(f"Disruption Analysis for {product_id}", f"Risk Percentage: {analysis['risk_percentage']}%")


# Main Execution
def main():
    analyzer = InventoryAnalyzer()
    root = tk.Tk()
    app = InventoryApp(root, analyzer)
    root.mainloop()

if __name__ == "__main__":
    main()
