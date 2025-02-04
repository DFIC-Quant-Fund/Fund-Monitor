import pandas as pd
import matplotlib.pyplot as plt

def aggregate_data(input_file, output_file):
    df = pd.read_csv(input_file)
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.replace('', 0)
    numeric_columns = df.columns.drop('Date')
    df[numeric_columns] = df[numeric_columns].apply(pd.to_numeric, errors='coerce')

    df['Total_Portfolio_Value'] = df[numeric_columns].sum(axis=1)
    df_filtered = df[df['Total_Portfolio_Value'] > 0]
    output_df = df_filtered[['Date', 'Total_Portfolio_Value']].copy()
    output_df = output_df.sort_values('Date')
    output_df['pct_change'] = output_df['Total_Portfolio_Value'].pct_change()

    output_df.to_csv(output_file, index=False, float_format='%.2f')

def plot():

    df = pd.read_csv('output/portfolio_total.csv')
    df['Date'] = pd.to_datetime(df['Date'])
    fig, ax = plt.subplots(figsize=(12, 6))

    ax.plot(df['Date'],df['Total_Portfolio_Value'],color='black',linewidth=2,label='Portfolio Value')
    ax.set_title('Portfolio Value CAD', fontsize=16, fontweight='bold')
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Portfolio Value ($)', fontsize=12)
    ax.legend(loc='lower right')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig('output/portfolio_plot.png')

def main():
    input_file = "output/market_values.csv"
    output_file = "output/portfolio_total.csv"
    aggregate_data(input_file, output_file)

main()
plot()


