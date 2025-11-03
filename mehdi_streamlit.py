
import os 
import json
import plotly.graph_objects as go 
import pandas as pd
import geopandas as gpd
import matplotlib
import plotly.express as px
import shapely
from shapely.geometry import Point, LineString, Polygon, MultiPolygon
import streamlit as st
import time
st.set_page_config(
    page_title="Mon App",
    layout="wide"  # <--- rend le main container plus large
)

with st.container():
    st.title('Are Wind and Solar Energy Productions Complementary?')
    directory = 'data/Pickles'

    regions = gpd.read_file("data/regions/regions.txt")
    regions_metropole = regions.drop([9,10,11,12,13,17],axis=0)
    regions_metropole = regions_metropole.reset_index(drop=True)
    df_solar = pd.read_pickle(directory + '/df_solaire_norm.pkl')
    df_wind = pd.read_pickle(directory + '/df_eolien_norm.pkl')
    import numpy as np
    def color_coding(df):
        percentiles = df.value.quantile([0.33, 0.66])
        color = np.array(["Low "]*len(df))
        color[df.value>percentiles.iloc[0]] = "Mid "
        color[df.value>percentiles.iloc[1]] = "High"
        df['color'] = color
        return df
    def preprocess(df,upsampling,regions_metropole,normalized=False):
        region_surface_area = {
        'Auvergne-Rhône-Alpes': 69711,
        'Bourgogne-Franche-Comté': 47783,
        'Bretagne': 27208,
        'Centre-Val de Loire': 39151,
        'Grand Est': 57433,
        'Hauts-de-France': 31814,
        'Normandie': 29907,
        'Nouvelle-Aquitaine': 84036,
        'Occitanie': 72724,
        'Pays de la Loire': 32082,
        "Provence-Alpes-Côte d'Azur": 31400,
        'Île-de-France': 12012,
    }

        df.rename(columns={'PACA':"Provence-Alpes-Côte d'Azur",'Pays-de-la-Loire':"Pays de la Loire",'Ile-de-France':'Île-de-France','Grand-Est':'Grand Est'},inplace=True)
        df = pd.DataFrame(df.resample('1h').mean())
        df = df.resample(upsampling,origin='end_day').sum()
        df = df.T
        df_reset = df.reset_index()
        df_melted = df_reset.melt(id_vars='Périmètre',value_vars=df.columns)
        my_dict = dict(zip(regions_metropole['nom'], regions_metropole['code']))
        df_melted['region_id'] = df_melted['Périmètre'].map(my_dict)
        if normalized:
            surf = df_melted['Périmètre'].map(region_surface_area)
            df_melted.value = df_melted.value/surf
        df_melted= color_coding(df_melted)
        return df_melted
    regions_metropole.index = regions_metropole.code
    wind = preprocess(df_wind,'1h',regions_metropole,normalized=False)
    solar = preprocess(df_solar,'1h',regions_metropole,normalized=False)

    both = wind.merge(right=solar,how='inner',on=['DateTime','Périmètre'],suffixes=['_wind','_solar']).drop(columns='region_id_solar')
    temp = both.groupby('DateTime')[['value_wind','value_solar']].sum()
    temp['hour'] = temp.index.hour
    data = temp.groupby('hour').mean()
    data_norm = data.apply(lambda x: (x - x.min())/(x.max() - x.min())).copy()



    def add_data_to_figure(fig, x, y, label="no label", color="red",marker_size=4, line_width=1, opacity=1):
        
        fig.add_trace(
            go.Scatter(
                x=x, y=y, 
                mode='lines+markers', # try only lines and you'll see that lasso and box select dissapear when there are too many datapoints
                name=label,
                line=dict(color=color, width=line_width),
                marker=dict(size=marker_size),
                connectgaps=True,
                opacity=opacity
        ))

        return fig

    ROOT = '.'
    path_css = os.path.join(ROOT, 'static')

    if not os.path.exists(path_css):
        os.mkdir(path_css)

    filename = "style.json"
    fpath_styling = os.path.join(path_css, filename)
    with open(fpath_styling, 'r') as file:
        font = json.load(file)
        print(json.dumps(font, indent=4,))

        x = np.array(range(24))
    # trace 3: average temperature - smoothed
    y = data_norm.value_solar
    label = 'Solar'
    color = font['color']['primary']
    lw = font['line width'] + 3.5
    ms = 15
    plot_args3 = (x, y, label, color, ms,lw)

    # trace 4: energy consumption - smoothed
    y2 = data_norm.value_wind
    label = "Wind"
    color = font['color']['secondary']
    lw = font['line width'] + 3.5
    plot_args4 = (x, y2, label, color, ms,lw)
    fig = go.Figure()


    add_data_to_figure(fig, *plot_args3)

    fig.add_trace(go.Scatter(
        x=x, y=y2,
        name = 'Difference',
        fill='tonexty',
        line=dict(width=0),
        marker=dict(size=0),
        fillcolor='rgba(0,100,80,0.07)',  # base color
        showlegend=True,
        hoverinfo='skip',
        # PATTERN options
        fillpattern=dict(
            shape="/",       # '/', '\\', 'x', '+', '.', '-', '|'
            fgcolor='green', # color of pattern lines
            size=10,         # spacing
            solidity=0.2     # transparency of pattern lines
        )
    ))

    add_data_to_figure(fig, *plot_args4)

    fig.update_layout(
        height=600, width=1200,
        autosize=False,
        xaxis=dict(title="Hours of the Day"),
        yaxis=dict(title="Relative Energy Production"),
        xaxis_title=dict(font=dict(size=20)),
        yaxis_title=dict(font=dict(size=20)),
        legend=dict(
            font=dict(
                size=18  # Set legend font size here
            )
        ))
    fig.update_xaxes(tickfont=dict( size=18))
    fig.update_yaxes(tickfont=dict(size=18))
    fig.update_layout(title={
            'text': "Hourly Production of Wind/Solar Energy",   # Title text
            'x': 0.5,                      # Center the title horizontally
            'xanchor': 'center'            # Anchor the title at its center
        },
        title_font=dict(size=24) ,
        plot_bgcolor='white',  # Background color of plotting area
        paper_bgcolor='white'  # Background color of entire figure
    )
    fig.update_xaxes(
        showline=True,       # Show axis line
        linecolor='black',   # Axis line color
        linewidth=2,         # Axis line width
        mirror=True,         # Draw axis line on all sides
        tickfont=dict(color='black'),  # Tick labels color
        range=[-0.3, 23.3]
    )

    fig.update_yaxes(
        showline=True,
        linecolor='black',
        linewidth=2,
        mirror=True,
        tickfont=dict(color='black'),
        range=[-0.03, 1.03]
    )





    color_discrete_map = {
        'Low -Low ': '#e8e8e8',
        'Mid -Low ': '#ace4e4',
        'High-Low ': '#5ac8c8',
        'Low -Mid ': '#dfb0d6',
        'Mid -Mid ': '#a5add3',
        'High-Mid ': '#5698b9',
        'Low -High': '#be64ac',
        'Mid -High': '#8c62aa',
        'High-High': '#3b4994'
    }
    category_orders = {
        'color': ['Low -Low ', 'Mid -Low ', 'High-Low ', 
                'Low -Mid ', 'Mid -Mid ', 'High-Mid ',
                'Low -High', 'Mid -High', 'High-High']
    }
    labels = {
        'Low -Low ': 'Low Wind/ Low Solar',
        'Mid -Low ': 'Mid Wind/ Low Solar',
        'High-Low ': 'High Wind/ Low Solar',
        'Low -Mid ': 'Low Wind/ Mid Solar',
        'Mid -Mid ': 'Mid Wind/ Mid Solar',
        'High-Mid ': 'High Wind/ Mid Solar',
        'Low -High': 'Low Wind/ High Solar',
        'Mid -High': 'Mid Wind/ High Solar',
        'High-High': 'High Wind/ High Solar'
    }
    
    normalized_by_area = True
    wind = preprocess(df_wind,'1YE',regions_metropole,normalized=normalized_by_area)
    wind.region_id = wind.region_id.astype('int')
    wind_ = pd.DataFrame(wind.groupby('Périmètre')[['value','region_id']].mean(),columns=['value','region_id'])
    wind_.region_id = wind_.region_id.astype(int).astype(str)
    wind = color_coding(wind_)

    solar = preprocess(df_solar,'1YE',regions_metropole,normalized=normalized_by_area)
    solar.region_id = solar.region_id.astype('int')
    solar_ = pd.DataFrame(solar.groupby('Périmètre')[['value','region_id']].mean(),columns=['value','region_id'])
    solar_.region_id = solar_.region_id.astype(int).astype(str)# solar_['region_id'] = solar.region_id[:12].values
    solar = color_coding(solar_)

    both = wind.merge(right=solar,how='inner',on=['Périmètre'],suffixes=['_wind','_solar']).drop(columns='region_id_solar')
    both['color'] = both.color_wind+ '-' + both.color_solar
    data = both
    fig_map = px.choropleth_map(data_frame=data,  
        geojson=regions_metropole,
        locations="region_id_wind",  
        color="color",
        # animation_frame="DateTime",  
        # animation_group="region_id_wind",  
                            map_style="white-bg",
                            zoom=4.75, center = {"lat": 47, "lon": 1.5},width=800,height=700,title=f"Solar/Wind Energy Production Yearly Average Normalized by Surface Area",
                            color_discrete_map=color_discrete_map,
                            category_orders={'color': list(labels.keys())},
                            labels=labels,
                            hover_name = data.index,
                            hover_data={"value_wind":True,
                                        "value_solar":True,
                                        "region_id_wind":False})
    # fig_map.layout.updatemenus[0].buttons[0].args[1]['frame']['duration'] = 1500  # Duration of each frame (500 ms)
    for trace in fig_map.data:
        if trace.name in labels:
            trace.name = labels[trace.name]

    # fig_map.add_annotation(
    #     text="Productions of both are localized in specific regions.",  # the text you want to show
    fig_map.update_layout(annotations=[
            dict(
                text="Productions of both are localized in specific regions.",
                x=0.5,
                y=1.06,  # slightly below the main title
                xref='paper',
                yref='paper',
                showarrow=False,
                font=dict(size=20, color='darkgray')
            )],
            legend=dict(
            font=dict(
                size=18  # Set legend font size here
            )),
            title_font=dict(size=24)
        )
    fig_map.show()




    st.plotly_chart(
        fig,
        width = 1200,
        use_container_width=False,   # IMPORTANT: prevents Streamlit from forcing square
        config={"responsive": False} # prevent Plotly from auto-resizing
    )

    st.plotly_chart(
        fig_map,
        width=1200,
        use_container_width=False,   # IMPORTANT: prevents Streamlit from forcing square
        config={"responsive": False} # prevent Plotly from auto-resizing
    )