FROM node:20-alpine as base
WORKDIR /app

FROM base as development
RUN npm install
EXPOSE 3000
CMD ["npm", "run", "dev", "--", "--host"]

FROM base as build
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine as production
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
